"""Natural-language query handling: fillers stripped, my-area detected (offline)."""
from farmcast.web.webhook_whatsapp import extract_place, is_self_reference


def test_extract_place_strips_fillers():
    assert extract_place("how is the weather today at my area") == ""
    assert extract_place("will it rain tomorrow in Santa?") == "santa"
    assert extract_place("rain for kumbo?") == "kumbo"


def test_self_reference():
    assert is_self_reference("how is the weather today at my area")
    assert is_self_reference("rain at my farm")
    assert is_self_reference("weather here?")
    assert not is_self_reference("rain for kumbo")
    assert not is_self_reference("will it rain tomorrow in Santa?")
