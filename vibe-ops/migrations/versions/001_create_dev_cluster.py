# migrations/versions/001_create_dev_cluster.py
"""Create dev cluster tables: roadmaps, features, backlog_tasks, changelogs

Revision ID: 001
Revises: 
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '001'
down_revision = None

def upgrade():
    # Ler e executar o script SQL acima
    with open('migrations/001_create_dev_cluster_tables.sql', 'r') as f:
        op.execute(f.read())

def downgrade():
    # Rollback seguro: drop em ordem de dependência
    op.execute("DROP VIEW IF EXISTS v_dashboard_study_dev")
    op.execute("DROP TABLE IF EXISTS changelogs")
    op.execute("DROP TABLE IF EXISTS backlog_tasks")
    op.execute("DROP TABLE IF EXISTS features")
    op.execute("DROP TABLE IF EXISTS roadmaps")
