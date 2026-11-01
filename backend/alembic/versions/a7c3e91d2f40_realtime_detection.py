"""realtime detection: anomaly cool-down column + time indexes for RED windows/retention

Revision ID: a7c3e91d2f40
Revises: fc917be06f8d
Create Date: 2026-10-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7c3e91d2f40"
down_revision: Union[str, None] = "fc917be06f8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anomalies", sa.Column("last_firing_unix_nano", sa.BigInteger(), nullable=True))
    op.create_index("ix_spans_start", "spans", ["start_time_unix_nano"])
    op.create_index("ix_metric_points_time", "metric_points", ["time_unix_nano"])
    op.create_index("ix_log_records_time", "log_records", ["time_unix_nano"])


def downgrade() -> None:
    op.drop_index("ix_log_records_time", table_name="log_records")
    op.drop_index("ix_metric_points_time", table_name="metric_points")
    op.drop_index("ix_spans_start", table_name="spans")
    op.drop_column("anomalies", "last_firing_unix_nano")
