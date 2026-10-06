"""Agent outage fallback: with no AI keys, farmers still get a real answer."""
from farmcast.core import agent


def test_agent_falls_back_without_keys(tmp_path, monkeypatch):
    db = str(tmp_path / "a.db")
    monkeypatch.setenv("DATABASE_PATH", db)
    monkeypatch.setattr("farmcast.config.settings.OPENROUTER_API_KEY", "")
    monkeypatch.setattr("farmcast.config.settings.NVIDIA_API_KEY", "")
    for mod in ("farmcast.db.repo", "farmcast.web.webhook_whatsapp",
                "farmcast.core.agent"):
        try:
            monkeypatch.setattr(f"{mod}.settings.DATABASE_PATH", db)
        except Exception:
            pass
    # settings object is shared; also patch module-level copies
    import farmcast.config.settings as s
    monkeypatch.setattr(s, "DATABASE_PATH", db)
    from farmcast.db import repo
    repo.init_db(db)
    lid = repo.get_or_create_locality("Kumbo", 6.2, 10.6667, 1800, "Bui")
    con = repo.connect(db)
    con.execute("INSERT INTO farmers(phone,name,locality_id,crop) VALUES(?,?,?,?)",
                ("237009", "Fallback", lid, "maize"))
    con.commit()
    con.close()
    out = agent.respond("237009", "how is the weather today in my area")
    assert out and "kumbo" in out.lower()


def test_compose_backstop_without_keys(monkeypatch):
    monkeypatch.setattr("farmcast.config.settings.OPENROUTER_API_KEY", "")
    monkeypatch.setattr("farmcast.config.settings.NVIDIA_API_KEY", "")
    out = agent._compose({"name": "T", "crop": "maize", "area": "Kumbo"},
                         "rain?",
                         weather={"place": "Kumbo", "mm": 5.8,
                                  "mm_label": "next 24 hours",
                                  "advice": "Good for planting."})
    assert "5.8mm" in out and "Kumbo" in out
