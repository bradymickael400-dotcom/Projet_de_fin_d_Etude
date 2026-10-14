"""Stockage local prive et atomique des documents ARGOS."""

import hashlib
import os
from pathlib import Path

from flask import current_app


def private_storage_root():
    configured = current_app.config.get("PRIVATE_STORAGE_PATH") or os.getenv("PRIVATE_STORAGE_PATH")
    root = Path(configured or (Path(current_app.instance_path).parent / "private_documents"))
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def store_private_document(relative_key, content):
    root = private_storage_root()
    target = (root / relative_key).resolve()
    if root not in target.parents:
        raise ValueError("Chemin de document invalide")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(target)
    return {
        "storage_key": str(target.relative_to(root)),
        "size": len(content),
        "checksum": hashlib.sha256(content).hexdigest(),
    }


def resolve_private_document(relative_key):
    root = private_storage_root()
    target = (root / relative_key).resolve()
    if root not in target.parents or not target.is_file():
        return None
    return target
