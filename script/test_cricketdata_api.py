from cricapi_client import CricAPIClient

def test_get_county_fixtures():
    """Test that we can get County Championship fixtures."""
    client = CricAPIClient()
    fixtures = client.get_county_fixtures()
    
    # Check that we got some fixtures
    assert len(fixtures) > 0
    
    # Check that each fixture has the required fields
    for fixture in fixtures:
        assert "match_id" in fixture
        assert "competition" in fixture
        assert "home_team" in fixture
        assert "away_team" in fixture
        assert "start_date" in fixture
        assert "end_date" in fixture
        assert "start_time_gmt" in fixture
        assert "venue" in fixture
        
        # Check that the competition is one of the County Championship divisions
        assert fixture["competition"] in [
            "County Championship Division One",
            "County Championship Division Two"
        ]

if __name__ == "__main__":
    test_get_county_fixtures() 