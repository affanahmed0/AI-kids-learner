"""Add games name and Id1

Revision ID: 31f8b4e83fd3
Revises: 0e7919b2f566
Create Date: 2024-12-28 18:01:23.222999

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '31f8b4e83fd3'
down_revision = '0e7919b2f566'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'game', type_='foreignkey')
    op.drop_column('game', 'user_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('game', sa.Column('user_id', sa.INTEGER(), nullable=True))
    op.create_foreign_key(None, 'game', 'user', ['user_id'], ['id'])
    # ### end Alembic commands ###
