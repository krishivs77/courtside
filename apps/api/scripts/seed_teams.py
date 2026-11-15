from nba_api.stats.static import teams
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db import engine
from app.models import Team


def seed_teams():
    nba_teams = teams.get_teams()

    if len(nba_teams) != 30:
        raise RuntimeError(
            f"Expected 30 NBA teams, received {len(nba_teams)}"
        )

    with engine.begin() as connection:
        for nba_team in nba_teams:
            values = {
                "external_id": str(nba_team["id"]),
                "name": nba_team["full_name"],
                "abbreviation": nba_team["abbreviation"],
            }

            statement = insert(Team).values(**values)

            statement = statement.on_conflict_do_update(
                index_elements=["external_id"],
                set_={
                    "name": statement.excluded.name,
                    "abbreviation": statement.excluded.abbreviation,
                },
            )

            connection.execute(statement)

        count = connection.scalar(
            select(func.count()).select_from(Team)
        )

    print(f"NBA teams imported successfully: {count}")


if __name__ == "__main__":
    seed_teams()
