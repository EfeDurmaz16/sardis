"""Credential-free validation for Sardis OpenClaw manifests and registry."""

from __future__ import annotations

import json
from pathlib import Path

from sardis_openclaw import SKILL_REGISTRY, get_executable_skill, get_skill, list_skills

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} is missing frontmatter"
    raw = text.split("---", 2)[1]
    values: dict[str, object] = {}
    for line in raw.splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def test_clawhub_manifest_is_public_and_credential_safe() -> None:
    manifest = json.loads((PACKAGE_ROOT / "clawhub.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "sardis"
    assert manifest["license"] == "MIT"
    assert manifest["repository"] == "https://github.com/EfeDurmaz16/sardis"
    assert manifest["env"] == ["SARDIS_API_KEY"]
    assert "network" in manifest["permissions"]


def test_skill_markdown_frontmatter_matches_package_layout() -> None:
    root_skill = frontmatter(PACKAGE_ROOT / "SKILL.md")
    assert root_skill["name"] == "sardis"
    assert root_skill["version"] == "1.1.0"

    skill_dirs = sorted((PACKAGE_ROOT / "skills").glob("sardis-*"))
    assert skill_dirs, "expected OpenClaw sub-skill directories"

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        metadata = frontmatter(skill_file)
        assert metadata["name"] == skill_dir.name
        assert metadata["version"] == "1.0.0"
        text = skill_file.read_text(encoding="utf-8")
        assert "SARDIS_API_KEY" in text
        assert "sk_live_" not in text
        assert "sk_test_" not in text


def test_python_registry_exports_executable_skills() -> None:
    assert {"create_wallet", "send_payment", "balance_check", "policy_update"}.issubset(
        SKILL_REGISTRY
    )

    payment_definition = get_skill("send_payment")
    assert payment_definition is not None
    assert payment_definition.category == "payment"

    wallet_skills = list_skills(category="wallet")
    assert {skill.name for skill in wallet_skills} == {"create_wallet", "balance_check"}

    executable = get_executable_skill("send_payment")
    assert executable.name == "send_payment"
    assert "wallet:write" in executable.required_permissions
