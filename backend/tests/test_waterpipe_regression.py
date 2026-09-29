import pytest

from app.models.enums import Category
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


@pytest.mark.parametrize("provider", [RuleBasedTriage(), SimulatedTriage()])
@pytest.mark.parametrize("text", ["i have a waterpipe problem", "Both WATERPIPES are broken"])
def test_compound_waterpipe_word(provider, text):
    assert provider.triage(text, "Test location").category == Category.water


def test_keyword_does_not_match_inside_unrelated_word():
    assert (
        RuleBasedTriage().triage("waterpipelineart exhibition", "Hall").category == Category.other
    )
