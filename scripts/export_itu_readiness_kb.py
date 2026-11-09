#!/usr/bin/env python3
"""Exporte le corpus validé ARGOS en dossiers compatibles avec le notebook ITUAIReadiness."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.knowledge.sources import source_register  # noqa: E402


PARTITIONS = ("operator", "customs_port", "data_protection", "legal_adviser")


def export_corpus(output_dir: Path) -> dict:
    documents_root = ROOT / "knowledge_base" / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = source_register(documents_root)
    accepted = [
        entry for entry in entries
        if entry.get("path")
        and entry.get("verification_status") in {
            "VERIFIED_PRIMARY_REFERENCE", "VERIFIED_SUMMARY_OF_PRIMARY",
            "VERIFIED_PRIMARY_EXCERPT_MANUALLY_TRANSCRIBED",
        }
        and (documents_root / entry["path"]).is_file()
    ]
    summary = {"schema_version": 1, "source_register_reviewed": "2026-10-29", "partitions": {}}
    for partition in PARTITIONS:
        destination = output_dir / partition / "docs"
        destination.mkdir(parents=True, exist_ok=True)
        manifest_entries = []
        for entry in accepted:
            if partition not in (entry.get("partitions") or []):
                continue
            source_path = (documents_root / entry["path"]).resolve()
            if documents_root.resolve() not in source_path.parents:
                continue
            target_name = Path(entry["path"]).name
            target = destination / target_name
            shutil.copyfile(source_path, target)
            manifest_entries.append({
                "doc_id": entry["doc_id"],
                "title": entry["title"],
                "source_file": target_name,
                "official_url": entry["official_url"],
                "jurisdiction": entry["jurisdiction"],
                "verification_status": entry["verification_status"],
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            })
        (output_dir / partition / "manifest.json").write_text(
            json.dumps({"partition": partition, "documents": manifest_entries}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        empty_notice = (
            "No document is currently verified for this partition. Keep its index empty; do not substitute another role's documents.\n\n"
            if not manifest_entries else ""
        )
        partition_readme = (
            "# ARGOS source partition: " + partition + "\n\n" + empty_notice
            + "Copy the `docs/` directory contents into the `docs` input folder of the official "
            + "[ITUAIReadiness Colab notebook](https://colab.research.google.com/github/CrashingGuru/ITUAIReadiness/blob/main/Colab%20Free%20Tier%20LLM%20Notebook.ipynb). "
            + "Build and keep a separate FAISS index for this partition. The notebook's default retrieval "
            + "does not enforce role authorization by itself; do not merge these indexes for multi-role use.\n\n"
            + "The adjacent manifest contains source provenance and SHA-256 hashes. Only entries marked "
            + "verified primary sources, manually checked primary excerpts, or reviewed summaries are exported. Unverified sources are deliberately omitted.\n"
        )
        (output_dir / partition / "README.md").write_text(partition_readme, encoding="utf-8")
        summary["partitions"][partition] = {"documents": len(manifest_entries), "path": str(destination)}
    (output_dir / "README.md").write_text(
        "# ARGOS → ITUAIReadiness knowledge-base export\n\n"
        "This export bridges the locally verified ARGOS source register to the ITUAIReadiness Colab notebook. "
        "Each institutional role has its own `docs/` folder and manifest. Import one role at a time, create a "
        "separate vector index, and retain the manifest next to the index. The notebook is a reference workflow; "
        "this export does not upload documents or indexes to an ITU service.\n\n"
        "Every input remains labelled with source authority, jurisdiction, verification state and official URL. "
        "The exported Markdown is an explanatory excerpt, not a replacement for the linked instrument.\n",
        encoding="utf-8",
    )
    (output_dir / "export_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "build" / "itu_ai_readiness_export"))
    args = parser.parse_args()
    summary = export_corpus(Path(args.output_dir).resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
