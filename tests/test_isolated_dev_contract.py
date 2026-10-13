"""Static regression contract for isolated development configuration."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_isolated_runner_has_no_network_mounts_or_ports():
    source = (ROOT / "compose.isolated-dev.yaml").read_text(encoding="utf-8")
    for line in ('network_mode: "none"', 'read_only: true', 'cap_drop: ["ALL"]',
                 'no-new-privileges:true', 'user: "10001:10001"',
                 "pids_limit:", "mem_limit:", "tmpfs:"):
        assert line in source
    # Match YAML mapping keys at line start only. For example,
    # "/app/reports:rw" is a tmpfs item, *not* a "ports:" property.
    for forbidden in ("volumes", "ports", "env_file", "privileged", "devices", "pid", "ipc"):
        assert re.search(rf"^\s*{forbidden}\s*:", source, flags=re.MULTILINE) is None
    assert "docker.sock" not in source


def test_dev_image_uses_unprivileged_user():
    source = (ROOT / "Dockerfile.dev").read_text(encoding="utf-8")
    assert "USER 10001:10001" in source
    assert "requirements-dev.txt" in source
    assert "COPY --chown=10001:10001 . /app" in source
    assert "-r requirements-web.txt -r requirements-dev.txt" in source
    assert "-r requirements.txt" not in source
