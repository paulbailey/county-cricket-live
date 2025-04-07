from datetime import datetime, timezone, timedelta
from script.fixture_extractor import group_fixtures_by_day
from script.models import Fixture, CompetitionType

def test_group_fixtures_by_day(mock_fixtures):
    """Test grouping fixtures by day."""
    today = datetime.now(timezone.utc).date()
    grouped = group_fixtures_by_day(mock_fixtures)
    
    # Check that we have entries for each day of the County Championship match
    for i in range(4):
        date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        assert date_str in grouped
        assert len(grouped[date_str]) == 2  # We have 2 fixtures per day

def test_group_fixtures_by_day_skips_past_matches(mock_fixtures):
    """Test that past matches are skipped when grouping fixtures."""
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    past_fixture = Fixture(
        match_id="past_match",
        competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
        home_team="Team A",
        away_team="Team B",
        start_date=yesterday,
        end_date=yesterday,
        start_time_gmt="11:00",
        venue="Ground 1"
    )
    
    fixtures = [past_fixture] + mock_fixtures
    grouped = group_fixtures_by_day(fixtures)
    
    # Check that yesterday's fixture is not included
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    assert yesterday_str not in grouped 