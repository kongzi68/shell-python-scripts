"""initial migration

Revision ID: 45696d17a671
Revises: 
Create Date: 2017-12-28 13:27:25.488586

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '45696d17a671'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('password', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('NORMAL', 'LIMIT', name='userstatusenum'), nullable=True),
    sa.Column('is_valid', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updateed_at', sa.DateTime(), nullable=True),
    sa.Column('loast_login', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('perms', sa.Enum('READ', 'WEIBO', 'COMMENT', 'ADMIN', name='permsenum'), nullable=True),
    sa.Column('is_valid', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updateed_at', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('roles')
    op.drop_table('users')
    # ### end Alembic commands ###
