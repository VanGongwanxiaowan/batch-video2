"""Example unit tests for the BatchShort project."""

def test_example():
    """Example test case."""
    assert 1 + 1 == 2


def test_environment(test_config):
    """Test that the test configuration is loaded correctly."""
    assert test_config["TESTING"] is True
    assert test_config["DEBUG"] is True
    assert test_config["DATABASE_URL"] == "sqlite:///:memory:"
