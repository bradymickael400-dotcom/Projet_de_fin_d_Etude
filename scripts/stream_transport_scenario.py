#!/usr/bin/env python3
"""Emit editable transport telemetry through ARGOS as an already-bound box."""

import argparse
import getpass
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "datasets" / "argos_central_africa_60min.json"


def api_json(session, method, url, **kwargs):
    response = session.request(method, url, timeout=30, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok:
        detail = payload.get("error") or payload.get("message") or response.text[:300]
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")
    return payload


def response_items(payload, collection_key, endpoint_name):
    """Accept a bare API list or the standard ARGOS collection envelope."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get(collection_key)
        if items is None and isinstance(payload.get("data"), dict):
            items = payload["data"].get(collection_key)
        if items is None:
            detail = payload.get("error") or payload.get("message") or "liste absente"
            raise RuntimeError(f"Réponse {endpoint_name} invalide : {detail}")
    else:
        raise RuntimeError(f"Réponse {endpoint_name} invalide : liste ou objet attendu")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise RuntimeError(f"Réponse {endpoint_name} invalide : '{collection_key}' doit être une liste d'objets")
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("ARGOS_URL", "http://localhost:5002"),
                        help="URL ARGOS (défaut: http://localhost:5002)")
    parser.add_argument("--box-id", required=True,
                        help="ID numérique de boîte ou identifiant de conteneur déjà associé (ex. 1 ou MSCU200900NNNNNN)")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                        help="Fichier JSON éditable des points à transmettre")
    parser.add_argument("--interval", type=float, default=None,
                        help="Pause entre deux points; par défaut celle du fichier de données")
    parser.add_argument("--start-index", type=int, default=0,
                        help="Index du premier point (0-based), pratique pour cibler un incident")
    parser.add_argument("--limit", type=int, default=0,
                        help="Nombre maximal de points à transmettre; 0 signifie tous")
    parser.add_argument("--no-route-update", action="store_true",
                        help="Conserver l'itinéraire attendu déjà configuré pour la boîte")
    parser.add_argument("--no-threshold-update", action="store_true",
                        help="Conserver les seuils déjà définis pour la boîte")
    args = parser.parse_args()
    if args.interval is not None and args.interval < 0:
        parser.error("--interval doit être positif ou nul")

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    is_synthetic = bool(dataset.get("synthetic") or dataset.get("simulation"))
    samples = dataset.get("samples") or []
    if not samples or not 0 <= args.start_index < len(samples):
        parser.error("Le jeu doit contenir des points et --start-index doit viser un point existant")
    end = len(samples) if not args.limit else min(len(samples), args.start_index + args.limit)
    interval = dataset.get("interval_seconds", 10) if args.interval is None else args.interval

    username = os.getenv("ARGOS_USERNAME") or input("Compte ARGOS autorisé pour cette boîte : ").strip()
    password = os.getenv("ARGOS_PASSWORD") or getpass.getpass("Mot de passe ARGOS : ")
    base_url = args.url.rstrip("/")
    session = requests.Session()
    auth = api_json(session, "POST", f"{base_url}/api/login",
                    json={"username": username, "password": password})
    token = auth.get("access_token")
    if not token:
        raise RuntimeError("La connexion ARGOS n'a pas fourni de jeton d'accès")
    session.headers.update({"Authorization": f"Bearer {token}"})

    boxes_payload = api_json(session, "GET", f"{base_url}/api/black-boxes/my-boxes")
    boxes = response_items(boxes_payload, "boxes", "my-boxes")
    requested = str(args.box_id).strip()
    if requested.isdigit():
        matches = [item for item in boxes if str(item.get("id_boite")) == requested]
    else:
        matches = [item for item in boxes if requested.casefold() in {
            str(item.get("container_id") or "").casefold(),
            str(item.get("numero_serie") or "").casefold(),
        }]
    if len(matches) != 1:
        raise RuntimeError("Boîte/conteneur introuvable ou ambigu dans votre périmètre ARGOS")
    selected = matches[0]
    box_id = int(selected["id_boite"])
    if str(selected.get("status") or "").casefold() != "active":
        raise RuntimeError(f"La boîte #{box_id} n'est pas active (état: {selected.get('status') or 'inconnu'})")
    container_type = str(selected.get("container_type") or "").casefold()
    if not selected.get("container_id"):
        raise RuntimeError(f"La boîte #{box_id} n'est liée à aucun conteneur")
    if any(word in container_type for word in ("demo", "synthetic", "synthétique")):
        raise RuntimeError(f"La boîte #{box_id} est rattachée à un conteneur synthétique; choisis une unité standard existante")

    history = api_json(session, "GET",
                       f"{base_url}/api/black-boxes/{box_id}/history?limit=2000")
    box = history.get("box") or {}
    device_uid = box.get("deviceUid")
    container_id = box.get("containerId")
    if not device_uid or not container_id:
        raise RuntimeError("Cette boîte n'a pas d'appareil actif associé à un conteneur existant")
    latest_positions = api_json(session, "GET", f"{base_url}/api/containers/positions")
    current_position = next((item for item in latest_positions
                             if str(item.get("id_boite")) == str(box_id)), {})
    latest_sequence = max(
        [int(point.get("sequence") or 0) for point in history.get("points", [])]
        + [int(current_position.get("sequence") or 0)]
        + [0]
    )
    sequence = latest_sequence + 1

    if not args.no_threshold_update and dataset.get("thresholds"):
        threshold_result = api_json(session, "POST", f"{base_url}/api/config/thresholds",
                                    json={"id_boite": box_id, **dataset["thresholds"]})
        if threshold_result.get("status") != "success":
            raise RuntimeError("Les seuils du scénario n'ont pas été appliqués")
        print("Seuils opérationnels ARGOS du scénario configurés pour cette boîte.")

    if not args.no_route_update:
        route = dataset["route"]
        route_result = api_json(session, "PUT",
            f"{base_url}/api/black-boxes/{box_id}/planned-route", json={
                "route_name": route["name"], "mode": route["mode"],
                "waypoints": route["waypoints"],
                "corridor_width_m": route["corridor_width_m"],
                "alert_threshold": route["alert_threshold"], "enabled": True,
            })
        print(f"Itinéraire actif : {route_result.get('route_name', route['name'])}")

    print(f"Boîte #{box_id} · conteneur {container_id} · appareil {device_uid} · type {selected.get('container_type') or 'standard'} · état appareil {selected.get('device_status') or 'inconnu'}")
    if str(selected.get("device_status") or "").upper() == "PENDING_ENROLLMENT":
        print("Injection par API terminal authentifiée; l'appareil physique n'est pas encore enrôlé.")
    print(f"Transmission des points {args.start_index + 1} à {end} sur {len(samples)} · intervalle {interval:g} s")
    for index in range(args.start_index, end):
        sample = samples[index]
        payload = {
            "messageId": str(uuid.uuid4()),
            "type": "telemetry",
            "deviceUid": device_uid,
            "blackBoxId": box_id,
            "containerId": container_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": sequence,
            "position": {**sample["position"], "source": "DEMO_SYNTHETIC" if is_synthetic else "DIRECT_WIFI"},
            "sensors": sample["sensors"],
            "modes": {"securityEnabled": True, "audioRecordingEnabled": False,
                      "audioListeningEnabled": False, "flameDetectionEnabled": True},
            "quality": {
                "timestampSource": "DEMO_SYNTHETIC" if is_synthetic else "DEVICE",
                "dataOrigin": "SYNTHETIC" if is_synthetic else "FIELD",
                "datasetId": str(dataset.get("dataset_id") or args.dataset.stem),
                "scenarioId": str(dataset.get("scenario_id") or "central_africa_demo"),
                "sampleLabel": str(sample.get("event") or "unlabelled"),
            },
        }
        result = api_json(session, "POST",
            f"{base_url}/api/black-boxes/{box_id}/direct-telemetry", json=payload)
        print(f"{index + 1}/{len(samples)} · séquence {sequence} · {sample.get('event', 'normal')} · {result.get('status', 'reçu')}", flush=True)
        sequence += 1
        if interval and index + 1 < end:
            time.sleep(interval)
    print("Flux terminé.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nFlux interrompu; les points déjà reçus restent enregistrés.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"Échec du flux ARGOS : {exc}", file=sys.stderr)
        raise SystemExit(1)
