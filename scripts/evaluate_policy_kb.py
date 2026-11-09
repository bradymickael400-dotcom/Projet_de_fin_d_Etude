#!/usr/bin/env python3
"""Évalue les requêtes de contrôle du corpus de politiques ARGOS."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.knowledge.rag import search_knowledge  # noqa: E402
from app.knowledge.sources import verified_source_paths  # noqa: E402


def main():
    control = json.loads((ROOT / "knowledge_base/ai_for_good_control_queries.json").read_text(encoding="utf-8"))
    output = []
    for item in control["queries"]:
        paths = verified_source_paths(item["partition"])
        hits = search_knowledge(item["query"], allowed_sources=paths, min_overlap=2)
        expected_source = item["expected_source"]
        if expected_source:
            matched = any(hit["source"] == expected_source for hit in hits)
            outcome = "PASS" if matched else "MISS_EXPECTED_SOURCE"
        else:
            matched = not hits
            outcome = "PASS" if matched else "REVIEW_FALSE_SUPPORT"
        output.append({
            "id": item["id"], "partition": item["partition"],
            "query": item["query"], "expected": item["expected"],
            "outcome": outcome,
            "retrieved": [{"source": h["source"], "lines": [h["line_start"], h["line_end"]], "score": h["score"]} for h in hits],
        })
    report = {
        "evaluation_id": control["evaluation_id"],
        "queries": output,
        "passed": sum(row["outcome"] == "PASS" for row in output),
        "total": len(output),
        "note": "PASS only checks source presence/absence for this small control set; it does not establish legal answer accuracy or comprehensive retrieval quality.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
