import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "key,value",
    [
        ("RATE_LIMIT_PER_MINUTE", 0),
        ("STATS_CACHE_TTL_SECONDS", -1),
        ("TRIAGE_CACHE_TTL_SECONDS", 0),
        ("AI_TIMEOUT_SECONDS", 0),
        ("AI_TIMEOUT_SECONDS", 11),
        ("AI_MAX_RETRIES", -1),
        ("AI_MAX_RETRIES", 2),
    ],
)
def test_invalid_runtime_limits_are_rejected(key, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{key: value})


def test_supported_runtime_limits():
    settings = Settings(_env_file=None, AI_TIMEOUT_SECONDS=5, AI_MAX_RETRIES=0)
    assert settings.AI_TIMEOUT_SECONDS == 5
    assert settings.AI_MAX_RETRIES == 0
