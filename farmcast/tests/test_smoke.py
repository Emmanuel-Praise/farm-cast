"""Smoke tests: resolver offline + rules pure logic (no network)."""
from farmcast.core.gazetteer import Gazetteer
from farmcast.core import rules


def test_gazetteer_exact_and_fuzzy(tmp_path):
    import os
    seed = os.path.join(os.getcwd(), "farmcast", "config", "localities_seed.csv")
    if not os.path.exists(seed):
        seed = os.path.join("config", "localities_seed.csv")
    g = Gazetteer()
    g.load_csv(seed)
    assert g.exact("kumbo") is not None
    assert g.exact("KUMBO").name == "Kumbo"
    assert g.fuzzy("kimbo").name == "Kumbo"  # typo tolerance
    assert g.exact("bamenda city").name == "Bamenda"  # alias expansion


def test_rules_categories():
    assert rules.categorize(50, [10, 10, 10, 10, 10]) == "HEAVY_RAIN"
    assert rules.categorize(20, [5, 5, 5, 5, 5]) == "RAIN"
    assert rules.categorize(7, [2, 2, 2, 2, 2]) == "LIGHT_RAIN"
    assert rules.categorize(0, [0, 0, 1, 0, 0]) == "DRY_SPELL"
    assert rules.categorize(0, [0, 0, 9, 0, 0]) == "DRY"


def test_rules_flags():
    assert "COLD" in rules.flags(8, 1800, 5, 0, 0)
    assert "COLD" not in rules.flags(12, 1800, 5, 0, 0)
    assert "HIGH_WIND" in rules.flags(20, 1200, 35, 0, 0)


def test_intent_parser():
    from farmcast.web.webhook_whatsapp import parse_intent, extract_place
    assert parse_intent("rain for kumbo?") == "FORECAST"
    assert parse_intent("when plant") == "PLANT"
    assert parse_intent("spray herbicide") == "SPRAY"
    assert extract_place("rain for kumbo?") == "kumbo"
