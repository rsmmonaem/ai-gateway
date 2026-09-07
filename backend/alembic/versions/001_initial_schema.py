"""Initial schema for users, api_keys, models, usage_records, permissions

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'])

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, server_default='Default Key'),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('monthly_limit_tokens', sa.BigInteger(), nullable=False, server_default='10000000'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_key_prefix', 'api_keys', ['key_prefix'])
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])

    op.create_table(
        'models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('aliases', sa.String(length=255), nullable=True),
        sa.Column('provider', sa.String(length=100), nullable=False, server_default='local'),
        sa.Column('backend', sa.String(length=50), nullable=False),
        sa.Column('backend_model_name', sa.String(length=255), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('context_length', sa.Integer(), nullable=False, server_default='32768'),
        sa.Column('supports_chat', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('supports_completion', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('supports_embeddings', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('supports_tools', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('supports_vision', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('pricing_input', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('pricing_output', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_models_slug', 'models', ['slug'], unique=True)

    op.create_table(
        'model_instances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('instance_name', sa.String(length=100), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('health_status', sa.String(length=50), nullable=False, server_default='ONLINE'),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('weight', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('backend', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('stream', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('client_ip', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('prompt_content', sa.Text(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_records_request_id', 'usage_records', ['request_id'], unique=True)
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_created_at', 'usage_records', ['created_at'])

    op.create_table(
        'user_model_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('allowed', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'model_id', name='uq_user_model')
    )

    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('system_settings')
    op.drop_table('user_model_permissions')
    op.drop_table('usage_records')
    op.drop_table('model_instances')
    op.drop_table('models')
    op.drop_table('api_keys')
    op.drop_table('users')
