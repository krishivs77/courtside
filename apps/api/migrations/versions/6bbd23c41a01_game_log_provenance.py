"""Record source game dates and ingestion provenance without inventing tipoff times."""
from alembic import op
import sqlalchemy as sa

revision = "6bbd23c41a01"
down_revision = "3059ea01819b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("game_date", sa.Date(), nullable=True))
    op.add_column("games", sa.Column("source", sa.String(80), nullable=True))
    op.add_column("games", sa.Column("timestamp_precision", sa.String(20), nullable=True))
    op.add_column("player_game_stats", sa.Column("source", sa.String(80), nullable=True))
    op.add_column("player_game_stats", sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("player_game_stats", "retrieved_at")
    op.drop_column("player_game_stats", "source")
    for column in ("timestamp_precision", "source", "game_date"):
        op.drop_column("games", column)
