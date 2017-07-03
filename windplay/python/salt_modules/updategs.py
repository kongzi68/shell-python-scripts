#!/usr/bin/env python
#coding=utf-8
# by colin on 2016-11-25
# revision on 2017-01-20

import ftplib
import glob
import os
import time
import zipfile
import psutil
import win32api
import win32gui
import win32con

# Import salt libs
import salt.utils
import salt.utils.find
import salt.utils.psutil_compat as spsutil

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# 定义需要被更新的程序目录的关键词
# 比如泰国：游戏服的程序目录关键词为：GS
# 世界服的程序目录关键词为：WS
# 还比如：国内游戏服的程序目录关键词为：3JianHaoServer
# dir_key = ['GS', 'WS']
dir_key = ['3JianHaoServer', 'WorldServer']
exclude_dir = ['test', 'bak', 'back', 'backup'] # 字母小写
# 泰国的系统是:"mm/dd/yyyy",国内的系统是:"yyyy/mm/dd"
date_type = '2050/01/01'

def ftp_get_file(update_file, ftpdir):
    '''
    FTP下载
    使用：salt 'win2008' updategs.ftp_get_file 'GameServer.zip' '20161130'
    '''
    ftpdir = str(ftpdir)
    update_file = str(update_file)
    ftp = ftplib.FTP()
    try:
        # ftp.connect('192.168.10.36', 21)
        # ftp.login('ftpuser', '123456')
        # ftp.connect('161.202.172.44', 21)
        # ftp.login('ftpuser', r'123456')
        ftp.connect('10.232.20.54', 21)
        ftp.login('ftptest', r'123456')
        ftp.cwd(ftpdir)
        ftp.retrbinary('RETR {0}'.format(update_file),
            open(update_file, 'wb').write)
        ftp.quit()
        return True
    except ftplib.all_errors:
        return False

def find(path, *args, **kwargs):
    '''
    查找文件
    函数的具体使用方法，用下面的命令获取帮助:
    salt 'win2008' sys.doc file.find
    '''
    if 'delete' in args:
        kwargs['delete'] = 'f'
    elif 'print' in args:
        kwargs['print'] = 'path'

    try:
        finder = salt.utils.find.Finder(kwargs)
    except ValueError as ex:
        return 'error: {0}'.format(ex)

    ret = [item for i in [finder.find(p) for p in
           glob.glob(os.path.expanduser(path))] for item in i]
    ret.sort()
    return ret

def file_zip(filename, filedir):
    '''
    解压zip压缩包到指定目录
    若目标目录有同名文件，且被进程占用，解压会报IOError错误
    就算有同名文件，若未被进程占用，是可以正确替换和更新的
    '''
    filename = str(filename)
    filedir = str(filedir)
    iszip = zipfile.is_zipfile(filename)
    if iszip:
        try:
            fz = zipfile.ZipFile(filename,'r')
            for file in fz.namelist():
                fz.extract(file, filedir)
            return True
        except IOError:
            return False
    else:
        return False

def disk_partitions():
    '''
    返回结果为列表，类是：['/', '/data']
    '''
    result = []
    disk_infos = [dict(partition._asdict()) for partition in
                  spsutil.disk_partitions('False')]
    for item in disk_infos:
        if item['fstype'] == 'NTFS':
            result.append(item['mountpoint'])
    return result

def get_gs_path(t_file):
    '''
    获取有效的ServerConfig.xml配置文件路径
    '''
    result = []
    t_file = str(t_file)
    for item in disk_partitions():
        files = find(item, type='f', name=t_file)
        if files:
            for tfile in files:
                gsdir = tfile.split('\\')[1].lower()
                i = 0
                for tkey in exclude_dir:
                    if tkey in gsdir: i += 1
                if i > 0:
                    continue
                else:
                    for t_item in dir_key:
                        if t_item.lower() in gsdir: result.append(tfile)

    return result


class RestartGSM(object):
    '''
    重启"GameServerMannage.exe"，以下简称GSM
    说明：
        GSM在停服之后，经常会报错，因不懂C#，没法优化这个GSM程序，现通过python脚本方式
        实现每次停服更新游戏时，关闭现有的GSM，并再次启动这些GSM。
    特别说明：
        只对拉起的GSM有效。
        只会重启报错的进程与未报错的进程，也就是能从进程中获取到的管理工具进程
        SO，第一次运行的时候，必须要手动拉起GSM
    '''
    def __init__(self):
        super(RestartGSM, self).__init__()
        self.date_type = date_type

    def class_main(self):
        '''
        类的主函数，梳理业务流程
        '''
        # 获取GSM进程清单
        self.ps_list = self.get_gsm_process_info('GameServerMannage.exe')
        time.sleep(2)
        # 获取到GSM清单之后，开始关闭进程
        self.clean_process()
        # 禁用使用空密码的本地账户只允许进行控制台登录
        self.mod_gpedit(0)
        time.sleep(2)
        # 启动GSM
        ret = self.start_gsm(self.ps_list)
        # 启用使用空密码的本地账户只允许进行控制台登录
        time.sleep(2)
        self.mod_gpedit(1)
        return ret

    def send_string(self, hwnd, msg):
        '''发送字符串,只能发送英文字符串'''
        for item in msg:
            win32api.SendMessage(hwnd, win32con.WM_CHAR, ord(item), 0)
        # 发送回车键
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

    def kill_process(self, ps_name):
        for ps_item in psutil.process_iter():
            if ps_item.name() == ps_name:
                ps_item.kill()

    def clean_process(self):
        '''关闭进程'''
        # 清理GSM报错产生的WerFault.exe进程
        self.kill_process('WerFault.exe')

        # 发送exit命令，关闭GS
        for ps_item in psutil.process_iter():
            try:
                if ps_item.name() == 'GameServerMannage.exe':
                    gsm_hwnd = win32gui.FindWindow(None, ps_item.exe())
                    self.send_string(gsm_hwnd, 'exit')
                    ps_item.kill() # 关闭正常退出GS后的GSM
            except Exception:
                pass

        # GSM报错退出后，未关闭的GS，将被强制结束进程
        self.kill_process('GameServer.exe')

    def get_gsm_process_info(self, ps_name):
        '''
        获取指定进程的路径清单
        返回的结果为嵌套列表：[[],[]]
        '''
        ret = []
        for ps_item in psutil.process_iter():
            try:
                if ps_item.name() == ps_name:
                    t_ret = [ps_item.exe(), ps_item.username()]
                    ret.append(t_ret)
            except Exception:
                pass
        return ret

    def get_gsm_process_status(self, ps_exe):
        '''判断进程是否启动'''
        ret = False
        for ps_item in psutil.process_iter():
            try:
                if ps_item.exe() == ps_exe:
                    ret = True
                    break
            except Exception:
                pass
        return ret

    def mod_gpedit(self, values):
        '''
        values：值为1时，表示启用使用空密码的本地账户只允许进行控制台登录
                值为0时，表示禁用，禁用之后计划任务才能免密码运行
        '''
        gp_str = """
        [Version]
        signature="$CHICAGO$"
        [Registry Values]
        MACHINE\System\CurrentControlSet\Control\Lsa\LimitBlankPasswordUse=4,{0}
        """.format(values)
        with open('gp.inf', 'wb') as gp:
            gp.write(gp_str)
            gp.flush
        os.system("secedit /configure /db gp.sdb /cfg gp.inf /quiet")
        os.system("del gp.sdb gp.inf")

    def create_restart_bat(self, bat_name, gs_dir):
        '''创建restart.bat'''
        bat_txt = """
                @echo off
                cd /d {0}
                start {0}\GameServerMannage.exe
                exit
                """.format(gs_dir)
        with open(bat_name, 'wb') as file:
            file.write(bat_txt)
            file.flush

    def start_gsm(self, ps_list):
        '''启动成独立的窗口运行'''
        bat_name = 'restart.bat'
        ret = []
        for item, user in ps_list:
            t_item = item.split('\\')[0:2]
            gs_dir = '{0}\\{1}'.format(t_item[0], t_item[1])
            if os.path.exists(gs_dir):
                os.chdir(gs_dir)
                if os.path.exists(item):
                    try:
                        self.create_restart_bat(bat_name, gs_dir)
                        schtask = """SCHTASKS /create /IT /RU {0} /tn saltsch /tr {1}\{2} /SC ONCE /SD {3} /ST 00:00 /F """.format(user, gs_dir, bat_name, self.date_type)
                        os.system(schtask)
                        os.system("SCHTASKS /run /tn saltsch")
                        time.sleep(1)  # 留一秒给GSM启动
                        os.system("SCHTASKS /delete /tn saltsch /F")
                        os.system("del {0}".format(bat_name))
                        time.sleep(1)  # 间隔一秒才检查状态，防闪退检查失败
                        if self.get_gsm_process_status(item):
                            ps_status = '{0}: restart success.'.format(item)
                        else:
                            ps_status = '{0}: restart failed!!!'.format(item)
                        ret.append(ps_status)
                    except Exception as e:
                        ret.append('{0}: {1}'.format(item, e))

        return ret


def restart_gsm():
    '''
    功能：重启GameServerMannage.exe
    使用：
        游戏服：salt -N GMServer updategs.restart_gsm
        世界服：salt -N WSServer updategs.restart_gsm
        备注：游戏服与世界服在/etc/salt/master中一定要分组
    特别说明：
        只对拉起的GSM有效。
        只会重启报错的进程与未报错的进程，也就是能从进程中获取到的管理工具进程
    '''
    restart = RestartGSM()
    return restart.class_main()

def upgrade(filename, ftpdir, doit=False):
    '''
    filename  更新包名称
    ftpdir  更新包在ftp中的目录名称
    doit  'True'表示更新，'False'表示测试
    游戏服：
        测试：salt -N GMServer updategs.upgrade 'GameServer.zip' '20161130'
        正式：salt -N GMServer updategs.upgrade 'GameServer.zip' '20161130' doit=True
    世界服：
        测试：salt -N WSServer updategs.upgrade 'WorldServer.zip' '20161130'
        正式：salt -N WSServer updategs.upgrade 'WorldServer.zip' '20161130' doit=True
    备注：游戏服与世界服在/etc/salt/master中一定要分组
    报错处理：
        F:\GS1:False，状态为False有两种情况：
            1、测试的时候，会显示为False；
            2、压缩包内的文件解压到目标文件夹时莫有权限，一般是该文件被进程占用
    '''
    result = []
    filename = str(filename)
    ftpdir = str(ftpdir)
    ftp_status = ftp_get_file(filename, ftpdir)
    if ftp_status:
        for item in get_gs_path('ServerConfig.xml'):
            t_item = item.split('\\')[0:2]
            gs_dir = '{0}\\{1}'.format(t_item[0], t_item[1])
            if doit:
                zip_status = file_zip(filename, gs_dir)
            else:
                zip_status = False
            if zip_status:
                result.append('{0}:True'.format(gs_dir))
            else:
                result.append('{0}:False'.format(gs_dir))
    else:
        return 'ftp error'
    os.remove(filename)
    return result