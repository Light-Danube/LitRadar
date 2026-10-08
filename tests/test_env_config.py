from __future__ import annotations

from config import RadarConfig


def test_env_file_controls_runtime_config(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LITRADAR_SOURCES=arxiv,openalex,arxiv\n"
        "LITRADAR_SOURCE_WORKERS=2\n"
        "LITRADAR_PERSONALIZATION_MIN_FEEDBACK=7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("config.ENV_PATH", env_file)
    for key in ["LITRADAR_SOURCES", "LITRADAR_SOURCE_WORKERS", "LITRADAR_PERSONALIZATION_MIN_FEEDBACK"]:
        monkeypatch.delenv(key, raising=False)
    config = RadarConfig.load()
    assert config.enabled_sources == ("arxiv", "openalex")
    assert config.source_workers == 2
    assert config.personalization_min_feedback == 7
