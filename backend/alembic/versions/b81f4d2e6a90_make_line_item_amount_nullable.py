"""Allow unknown line-item amounts to remain NULL."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b81f4d2e6a90"
down_revision: Union[str, Sequence[str], None] = "7ed0ffb0a9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "invoice_line_items",
        "amount",
        existing_type=sa.Numeric(precision=12, scale=2),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    has_null_amounts = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM invoice_line_items "
            "WHERE amount IS NULL"
            ")"
        )
    ).scalar()

    if has_null_amounts:
        raise RuntimeError(
            "Cannot downgrade: resolve NULL line-item amounts before "
            "making the amount column NOT NULL."
        )

    op.alter_column(
        "invoice_line_items",
        "amount",
        existing_type=sa.Numeric(precision=12, scale=2),
        nullable=False,
    )
