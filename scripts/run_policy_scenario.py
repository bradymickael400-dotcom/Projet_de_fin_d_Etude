#!/usr/bin/env python3
"""Rejoue localement le scénario institutionnel synthétique ARGOS."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.policy_scenario import run_policy_scenario  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="silent_container_v1")
    parser.add_argument("--output", help="Fichier JSON de sortie; stdout par défaut")
    args = parser.parse_args()
    result = run_policy_scenario(args.scenario)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"Scénario {args.scenario} terminé; trace {result['trace_id']} écrite dans {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
