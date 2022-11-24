"""added_suggestion_thread_columns

Revision ID: c9dab6e5335e
Revises: d701f9500009
Create Date: 2022-11-24 12:15:06.541568

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9dab6e5335e'
down_revision = 'd701f9500009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('GuildConfigurations', sa.Column('suggestion_channel', sa.BigInteger(), nullable=True))
    op.add_column('GuildConfigurations', sa.Column('use_suggestion_threads', sa.Boolean(), server_default='false', nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('GuildConfigurations', 'suggestion_channel')
    op.drop_column('GuildConfigurations', 'use_suggestion_threads')
    # ### end Alembic commands ###