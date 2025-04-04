import pytest
import os
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_environment():
    # Set up test environment variables
    os.environ["GOOGLE_API_KEY"] = "test_api_key"
    os.environ["BLUESKY_USERNAME"] = "test_username"
    os.environ["BLUESKY_PASSWORD"] = "test_password"
    
    # Create necessary directories if they don't exist
    test_dirs = [
        "public/data/fixtures",
        "public/data"
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Clean up after tests if needed
    pass 