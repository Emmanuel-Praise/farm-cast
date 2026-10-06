"""Onboarding helpers (offline)."""
from farmcast.core.agent import extract_name


def test_extract_name():
    assert extract_name("My name is Blessing") == "Blessing"
    assert extract_name("Blessing") == "Blessing"
    assert extract_name("i am john nkeng") == "John Nkeng"
    assert extract_name("hello?") is None
    assert extract_name("yes") is None
    assert extract_name("x") is None
