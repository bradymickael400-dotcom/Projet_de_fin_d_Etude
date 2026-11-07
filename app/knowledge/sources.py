"""Manifeste local et filtrage de sources documentaires vérifiées."""

import json
from pathlib import Path

from app.knowledge.rag import _corpus_root


def source_register(root=None) -> list[dict]:
    corpus = Path(root).resolve() if root else _corpus_root()
    path = corpus.parent / "source_register.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value.get("sources", []) if isinstance(value, dict) else []
    except (OSError, ValueError, TypeError):
        return []


def verified_source_paths(partition: str, root=None) -> list[str]:
    """Fail closed: seuls les sources primaires ou résumés de source contrôlés sont visibles."""
    return [
        str(item["path"])
        for item in source_register(root)
        if isinstance(item, dict)
        and item.get("path")
        and item.get("verification_status") in {
            "VERIFIED_PRIMARY_REFERENCE", "VERIFIED_SUMMARY_OF_PRIMARY",
            "VERIFIED_PRIMARY_EXCERPT_MANUALLY_TRANSCRIBED",
        }
        and partition in (item.get("partitions") or [])
    ]
