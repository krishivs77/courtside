from sqlalchemy import update

from app.db import engine
from app.models import Team

EAST = {
    "ATL", "BOS", "BKN", "CHA", "CHI",
    "CLE", "DET", "IND", "MIA", "MIL",
    "NYK", "ORL", "PHI", "TOR", "WAS",
}

WEST = {
    "DAL", "DEN", "GSW", "HOU", "LAC",
    "LAL", "MEM", "MIN", "NOP", "OKC",
    "PHX", "POR", "SAC", "SAS", "UTA",
}


def main():
    with engine.begin() as connection:
        east_result = connection.execute(
            update(Team)
            .where(Team.abbreviation.in_(EAST))
            .values(conference="East")
        )

        west_result = connection.execute(
            update(Team)
            .where(Team.abbreviation.in_(WEST))
            .values(conference="West")
        )

        print(f"Updated {east_result.rowcount} Eastern teams")
        print(f"Updated {west_result.rowcount} Western teams")

        if east_result.rowcount != 15 or west_result.rowcount != 15:
            raise RuntimeError("Expected 15 teams per conference")


if __name__ == "__main__":
    main()
