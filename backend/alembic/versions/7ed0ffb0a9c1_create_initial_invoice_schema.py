"""create_initial_invoice_schema

Revision ID: 7ed0ffb0a9c1
Revises: 
Create Date: 2026-09-09 06:09:49.857182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ed0ffb0a9c1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('vendor_name', sa.String(length=255), nullable=True),
        sa.Column('invoice_number', sa.String(length=100), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('tax', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_llm_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_hash', name='uq_invoices_file_hash')
    )
    op.create_index('idx_invoices_file_hash', 'invoices', ['file_hash'], unique=True)
    op.create_index('idx_invoices_status', 'invoices', ['status'], unique=False)
    op.create_index('idx_invoices_created_at', 'invoices', ['created_at'], unique=False)
    op.create_index('idx_invoices_vendor_number', 'invoices', ['vendor_name', 'invoice_number'], unique=False)

    # 2. Create invoice_line_items table
    op.create_table(
        'invoice_line_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_line_items_invoice_id', 'invoice_line_items', ['invoice_id'], unique=False)

    # 3. Create processing_logs table
    op.create_table(
        'processing_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('log_level', sa.String(length=10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_processing_logs_invoice_id', 'processing_logs', ['invoice_id'], unique=False)
    op.create_index('idx_processing_logs_created_at', 'processing_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_processing_logs_created_at', table_name='processing_logs')
    op.drop_index('idx_processing_logs_invoice_id', table_name='processing_logs')
    op.drop_table('processing_logs')

    op.drop_index('idx_line_items_invoice_id', table_name='invoice_line_items')
    op.drop_table('invoice_line_items')

    op.drop_index('idx_invoices_vendor_number', table_name='invoices')
    op.drop_index('idx_invoices_created_at', table_name='invoices')
    op.drop_index('idx_invoices_status', table_name='invoices')
    op.drop_index('idx_invoices_file_hash', table_name='invoices')
    op.drop_table('invoices')
