"""update prompt model add content remove description and variables

Revision ID: 6cd626c1fa33
Revises: 17e931a93b99
Create Date: 2025-11-28 22:53:33.257665

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6cd626c1fa33'
down_revision = '17e931a93b99'
branch_labels = None
depends_on = None


def upgrade():
    # Add content column to prompts table
    op.add_column('prompts', sa.Column('content', sa.Text(), nullable=True))

    # Remove description column from prompts table
    op.drop_column('prompts', 'description')

    # Remove variables column from prompt_versions table
    op.drop_column('prompt_versions', 'variables')


def downgrade():
    # Restore variables column to prompt_versions table
    op.add_column(
        'prompt_versions',
        sa.Column(
            'variables',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=True,
        ),
    )

    # Restore description column to prompts table
    op.add_column(
        'prompts',
        sa.Column('description', sa.VARCHAR(length=500), nullable=True),
    )

    # Remove content column from prompts table
    op.drop_column('prompts', 'content')
