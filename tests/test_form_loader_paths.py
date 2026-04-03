"""Path confinement for payor form loading."""
from __future__ import annotations

from pathlib import Path

from utils import form_loader


def test_safe_child_path_rejects_traversal(tmp_path):
    root = tmp_path.resolve()
    (root / "legit").mkdir()
    assert form_loader._safe_child_path(root, "legit", "appeal_form.txt") is not None
    sneaky = form_loader._safe_child_path(root, "..", "etc", "passwd")
    assert sneaky is None


def test_safe_child_path_accepts_nested_file(tmp_path):
    root = tmp_path.resolve()
    sub = root / "Aetna"
    sub.mkdir()
    target = sub / "appeal_form.txt"
    target.write_text("{{APPEAL_BODY}}", encoding="utf-8")
    resolved = form_loader._safe_child_path(root, "Aetna", "appeal_form.txt")
    assert resolved is not None
    assert resolved == Path(target).resolve()


def test_payer_match_key_unites_spaced_and_compact_names():
    assert form_loader._payer_match_key("United Healthcare") == form_loader._payer_match_key(
        "UnitedHealthcare"
    )


def test_find_form_matches_spaced_payer_to_compact_folder(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    uhc = root / "UnitedHealthcare"
    uhc.mkdir()
    (uhc / "appeal_form.txt").write_text("Body: {{APPEAL_BODY}}", encoding="utf-8")
    monkeypatch.setattr(form_loader, "_FORMS_ROOT", root)
    name, text = form_loader.find_form_for_payer("United Healthcare", request_type="appeal")
    assert name == "UnitedHealthcare"
    assert "Body:" in (text or "")
