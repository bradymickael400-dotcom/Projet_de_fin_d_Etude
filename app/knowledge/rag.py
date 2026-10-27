"""Récupération lexicale traçable pour les documents locaux autorisés.

Ce module ne télécharge ni n'invente de documents réglementaires. Les passages
proviennent uniquement des fichiers du corpus configuré par l'installation.
"""

import re
from pathlib import Path

from flask import current_app, has_app_context


TOKEN_RE = re.compile(r"[\wÀ-ÿ'-]{2,}", re.UNICODE)
SUPPORTED_SUFFIXES = {".md", ".txt", ".rst"}
MAX_FILES = 500
MAX_FILE_BYTES = 1_000_000
MAX_RESULTS = 5


def _corpus_root(configured=None) -> Path:
    if configured:
        return Path(configured).expanduser().resolve()
    if has_app_context():
        configured = current_app.config.get("KNOWLEDGE_BASE_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "knowledge_base" / "documents"


def _terms(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text)}


def _passages(path: Path, root: Path):
    try:
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            return
        resolved = path.resolve()
        if root not in resolved.parents:
            return
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    lines = content.splitlines()
    start = 1
    current = []
    for number, line in enumerate(lines + [""], start=1):
        if line.strip():
            current.append(line)
            continue
        passage = "\n".join(current).strip()
        if passage and not all(line.lstrip().startswith("#") for line in current):
            yield {
                "text": passage[:4000],
                "source": str(path.relative_to(root)),
                "line_start": start,
                "line_end": number - 1,
            }
        current = []
        start = number + 1


def search_knowledge(query: str, root=None) -> list[dict]:
    query_terms = _terms(query)
    if not query_terms:
        return []
    corpus = Path(root).resolve() if root else _corpus_root()
    if not corpus.is_dir():
        return []
    scored = []
    for index, path in enumerate(sorted(corpus.rglob("*"))):
        if index >= MAX_FILES:
            break
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        for item in _passages(path, corpus):
            terms = _terms(item["text"])
            overlap = query_terms & terms
            if overlap:
                item["score"] = round(len(overlap) / (len(query_terms) + 0.25 * len(terms)), 4)
                scored.append(item)
    scored.sort(key=lambda item: (-item["score"], item["source"], item["line_start"]))
    return scored[:MAX_RESULTS]
