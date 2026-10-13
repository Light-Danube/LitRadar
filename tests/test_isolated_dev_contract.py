"""Static regression contract for isolated development configuration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_isolated_runner_has_no_network_mounts_or_ports():
    source = (ROOT / "compose.isolated-dev.yaml").read_text(encoding="utf-8")
    for line in ('network_mode: "none"', 'read_only: true', 'cap_drop: ["ALL"]', 'no-new-privileges:true', 'user: "10001:10001"', "pids_limit:", "mem_limit:", "tmpfs:"):
        assert line in source
    assert "volumes:" not in source
    assert "ports:" not in source
    assert "docker.sock" not in source
    assert "env_file:" not in source


def test_dev_image_uses_unprivileged_user():
    source = (ROOT / "Dockerfile.dev").read_text(encoding="utf-8")
    assert "USER 10001:10001" in source
    assert "requirements-dev.txt" in source
    assert "COPY . /app" in source
