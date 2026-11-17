import pandas as pd
import pytest

from scripts.import_game_logs import get_minutes, get_stat


def test_missing_stat_is_not_invented_zero():
    with pytest.raises(ValueError, match="PTS"):
        get_stat(pd.Series({"PTS": float("nan")}), "PTS")


@pytest.mark.parametrize("value", [-1, 2.5, "bad"])
def test_invalid_stat_rejected(value):
    with pytest.raises(ValueError):
        get_stat(pd.Series({"PTS": value}), "PTS")


def test_minutes():
    assert get_minutes("32:30") == 32.5
    assert get_minutes(None) is None
    with pytest.raises(ValueError):
        get_minutes("32:99")


@pytest.mark.parametrize("matchup, expected", [
    ("GSW vs. LAL", ("GSW", "LAL", "GSW")),
    ("GSW @ LAL", ("LAL", "GSW", "GSW")),
])
def test_matchup(matchup, expected):
    from scripts.import_game_logs import parse_matchup
    assert parse_matchup(matchup) == expected


@pytest.mark.parametrize("matchup", ["GSW vs LAL", "GSW @ GSW", "GSW @ LAL extra"])
def test_invalid_matchup(matchup):
    from scripts.import_game_logs import parse_matchup
    with pytest.raises(ValueError):
        parse_matchup(matchup)
