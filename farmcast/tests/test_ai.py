"""AI fallback contract: providers may fail, callers must still answer."""
from farmcast.core import ai
from farmcast.web.webhook_whatsapp import answer_query


def test_ai_never_raises_without_keys(monkeypatch):
    monkeypatch.setattr("farmcast.config.settings.OPENROUTER_API_KEY", "")
    monkeypatch.setattr("farmcast.config.settings.NVIDIA_API_KEY", "")
    assert ai.chat("hello", {"name": "T", "crop": "maize"}) == ""
    assert ai.describe_image(b"xxx") == ""


def test_unknown_message_falls_back_to_menu(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr("farmcast.config.settings.OPENROUTER_API_KEY", "")
    monkeypatch.setattr("farmcast.config.settings.NVIDIA_API_KEY", "")
    db = str(tmp_path / "t.db")
    monkeypatch.setenv("DATABASE_PATH", db)
    monkeypatch.setattr("farmcast.db.repo.settings.DATABASE_PATH", db)
    monkeypatch.setattr("farmcast.web.webhook_whatsapp.repo.settings.DATABASE_PATH", db)
    from farmcast.db import repo
    repo.init_db(db)
    lid = repo.get_or_create_locality("Kumbo", 6.2, 10.6667, 1800, "Bui")
    con = repo.connect(db)
    con.execute("INSERT INTO farmers(phone,name,locality_id,crop) VALUES(?,?,?,?)",
                ("237000", "T", lid, "maize"))
    con.commit()
    con.close()
    # free-text with no intent and no AI keys -> help menu, never empty/exception
    out = answer_query("237000", "hello good morning my friend, how are you doing today really")
    assert out and len(out) > 10
    assert os.path.exists(db)
