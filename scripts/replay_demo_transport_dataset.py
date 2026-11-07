#!/usr/bin/env python3
"""Replay synthetic transport scenarios through the authenticated ARGOS API."""

import argparse
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "argos_demo_two_routes.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True, help="ARGOS bearer access token")
    parser.add_argument("--black-box-id", type=int, required=True)
    parser.add_argument("--device-uid", required=True)
    parser.add_argument("--container-id", default=None)
    parser.add_argument("--sequence-start", type=int, required=True,
                        help="Séquence supérieure au dernier numéro traité par le dispositif")
    parser.add_argument("--scenario", default="all", help="Identifiant de scénario ou all")
    parser.add_argument("--interval", type=float, default=0.55,
                        help="Pause réelle entre mesures; évite de dépasser la limite API ARGOS")
    parser.add_argument("--time-step-seconds", type=int, default=60,
                        help="Temps simulé entre mesures; la fenêtre IoT de 6 heures est respectée")
    parser.add_argument("--end-offset-minutes", type=int, default=None,
                        help="Décalage dans le passé de la fin; utile pour un scénario unique")
    parser.add_argument("--limit", type=int, default=0, help="0 rejoue toutes les mesures")
    args = parser.parse_args()
    if args.interval < 0 or args.time_step_seconds <= 0:
        parser.error("--interval doit être positif ou nul et --time-step-seconds strictement positif")

    batch = json.loads(DATASET.read_text(encoding="utf-8"))
    scenarios = batch["scenarios"] if args.scenario == "all" else [
        item for item in batch["scenarios"] if item["scenario_id"] == args.scenario
    ]
    if not scenarios:
        parser.error(f"Scénario inconnu: {args.scenario}")
    headers = {"Authorization": f"Bearer {args.token}", "Content-Type": "application/json"}
    base_url = args.base_url.rstrip("/")
    now = datetime.now(timezone.utc)
    sequence = args.sequence_start
    total = 0

    for scenario_index, scenario in enumerate(scenarios):
        samples = scenario["samples"][:args.limit or None]
        if not samples:
            continue
        route_response = requests.put(
            f"{base_url}/api/black-boxes/{args.black_box_id}/planned-route",
            headers=headers, json=scenario["planned_route_configuration"], timeout=20,
        )
        if not route_response.ok:
            raise SystemExit(f"Configuration route refusée ({route_response.status_code}): {route_response.text}")

        config = scenario["provisioning"]["black_box"]["initial_parameters"]
        threshold_response = requests.post(
            f"{base_url}/api/config/thresholds",
            headers=headers,
            json={
                "id_boite": args.black_box_id,
                "temp_max": config.get("temperature_max_c", 32),
                "humi_max": config.get("humidity_max_percent", 75),
                "choc_max": config.get("shock_max_g", 5),
                "pression_min": config.get("pressure_min_hpa", 995),
                "vitesse_max": config.get("speed_max_kmh", 90),
                "angle_max": 30,
            },
            timeout=20,
        )
        if not threshold_response.ok:
            raise SystemExit(f"Configuration des seuils refusée ({threshold_response.status_code}): {threshold_response.text}")

        duration_seconds = (samples[-1]["minute"] - samples[0]["minute"]) * args.time_step_seconds
        if args.end_offset_minutes is not None:
            end_offset_minutes = args.end_offset_minutes
        elif len(scenarios) > 1:
            remaining_scenarios = len(scenarios) - scenario_index - 1
            end_offset_minutes = round(remaining_scenarios * duration_seconds / 60)
        else:
            end_offset_minutes = 0
        playback_end = now - timedelta(minutes=end_offset_minutes)
        print(f"{scenario['scenario_id']}: {len(samples)} mesures; fin simulée {playback_end.isoformat()}")

        for index, sample in enumerate(samples):
            position, sensor = sample["position"], sample["sensors"]
            sample_time = playback_end - timedelta(
                seconds=(samples[-1]["minute"] - sample["minute"]) * args.time_step_seconds
            )
            payload = {
                "messageId": str(uuid.uuid4()),
                "type": "telemetry",
                "deviceUid": args.device_uid,
                "blackBoxId": args.black_box_id,
                "containerId": args.container_id,
                "timestamp": sample_time.isoformat(),
                "sequence": sequence,
                "position": {
                    "latitude": position["latitude"], "longitude": position["longitude"],
                    "accuracy": position.get("accuracy_m", 10), "speed": position["speed_kmh"],
                    "heading": position["heading_deg"], "source": "DEMO_SYNTHETIC",
                },
                "sensors": {
                    "temperature": sensor["temperature_c"], "humidity": sensor["humidity_percent"],
                    "shock": sensor["shock_g"], "pressure": sensor["pressure_hpa"],
                    "flameDetected": sensor.get("flame_detected", False),
                    "doorOpen": sensor["door_open"], "batteryLevel": sensor["battery_percent"],
                    "securityAlarm": sensor["security_alarm"],
                },
                "modes": {
                    "securityEnabled": True, "audioRecordingEnabled": False,
                    "audioListeningEnabled": False, "flameDetectionEnabled": True,
                },
                "quality": {"timestampSource": "DEMO_SYNTHETIC",
                            "dataOrigin": "SYNTHETIC",
                            "scenarioId": scenario["scenario_id"],
                            "datasetId": batch.get("dataset_id"),
                            "sampleLabel": sample.get("event", "unlabelled")},
            }
            response = requests.post(
                f"{base_url}/api/black-boxes/{args.black_box_id}/direct-telemetry",
                headers=headers, json=payload, timeout=30,
            )
            if not response.ok:
                raise SystemExit(
                    f"Mesure {scenario['scenario_id']}:{index} refusée "
                    f"({response.status_code}): {response.text}"
                )
            sequence += 1
            total += 1
            if index == 0 or index + 1 == len(samples) or (index + 1) % 10 == 0 or sample.get("event") != "stable":
                print(f"  {index + 1}/{len(samples)} HTTP {response.status_code} — minute simulée {sample['minute']}")
            if args.interval and index + 1 < len(samples):
                time.sleep(args.interval)

    print(f"Rejeu terminé : {total} mesures synthétiques dans {len(scenarios)} scénario(s), boîte #{args.black_box_id}.")


if __name__ == "__main__":
    main()
