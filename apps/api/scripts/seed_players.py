from nba_api.stats.static import players
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db import engine
from app.models import Player


def seed_players():
    nba_players = players.get_players()

    if not nba_players:
        raise RuntimeError("NBA player directory is empty")

    with engine.begin() as connection:
        for player in nba_players:
            statement = insert(Player).values(
                external_id=str(player["id"]),
                full_name=player["full_name"],
            )

            statement = statement.on_conflict_do_update(
                index_elements=["external_id"],
                set_={
                    "full_name": statement.excluded.full_name,
                },
            )

            connection.execute(statement)

        count = connection.scalar(
            select(func.count()).select_from(Player)
        )

    print(f"NBA players in database: {count}")


if __name__ == "__main__":
    seed_players()
