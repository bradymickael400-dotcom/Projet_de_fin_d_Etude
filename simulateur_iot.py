#!/usr/bin/env python3
"""Simulateur IoT ARGOS : télémétrie asynchrone Douala–Yaoundé–Bertoua.

Exemple (boîtier déjà enrôlé et affecté côté ARGOS) :
  python3 simulateur_iot.py simulate-route --device-uid ARGOS-ESP32-001 \
    --api-key CLE_APPAREIL --black-box-id 1 --container-id MSCU1234566

La génération est cadencée à 1 Hz. Une file et un thread d'envoi HTTP séparés
évitent que les appels réseau bloquent l'horloge de simulation. Les erreurs
réseau sont journalisées; chaque message garde le même UUID lors des reprises.
"""

import argparse
import fcntl
import json
import math
import os
import queue
import random
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests


ROUTE = (
    (4.0511, 9.7679),    # Douala
    (3.8480, 11.5021),   # Yaoundé
    (4.5773, 13.6846),   # Bertoua
)
DURATION_SECONDS = 600
DEVIATION_METERS = 8_000
SEQUENCE_RESERVATION_SIZE = DURATION_SECONDS


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def post_json(base_url, path, payload, headers=None):
    response = requests.post(
        f"{base_url.rstrip('/')}{path}", json=payload,
        headers=headers or {}, timeout=15,
    )
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    print(json.dumps({"status_code": response.status_code, "body": body},
                     ensure_ascii=False), flush=True)
    response.raise_for_status()
    return body


def cmd_provision(args):
    payload = {
        "black_box_id": args.black_box_id,
        "hardware_serial": args.hardware_serial,
        "firmware_version": args.firmware_version,
        "protocol_version": "1.0",
    }
    login = requests.post(
        f"{args.base_url.rstrip('/')}/api/login",
        json={"username": args.username, "password": args.password}, timeout=15,
    )
    login.raise_for_status()
    access_token = login.json().get("access_token")
    if not access_token:
        raise RuntimeError("Jeton d'authentification absent")
    post_json(args.base_url, "/api/iot/devices/provision", payload,
              {"Authorization": f"Bearer {access_token}"})


def cmd_enroll(args):
    post_json(args.base_url, "/api/iot/enroll", {
        "deviceUid": args.device_uid, "enrollmentToken": args.token,
    })


def _distance_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _route_point(progress):
    """Interpolation linéaire par distance le long des 3 villes du corridor."""
    lengths = [_distance_m(ROUTE[i], ROUTE[i + 1]) for i in range(len(ROUTE) - 1)]
    remaining = max(0.0, min(1.0, progress)) * sum(lengths)
    for index, length in enumerate(lengths):
        if remaining <= length or index == len(lengths) - 1:
            ratio = min(1.0, remaining / length) if length else 0.0
            a, b = ROUTE[index], ROUTE[index + 1]
            return (a[0] + (b[0] - a[0]) * ratio,
                    a[1] + (b[1] - a[1]) * ratio,
                    _bearing(a, b))
        remaining -= length
    return ROUTE[-1][0], ROUTE[-1][1], 0.0


def _bearing(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _offset_lateral(lat, lon, heading, distance_m):
    """Décale une position perpendiculairement à la route (approximation locale)."""
    side = math.radians(heading + 90)
    north_m = math.cos(side) * distance_m
    east_m = math.sin(side) * distance_m
    lat2 = lat + north_m / 111_320
    lon2 = lon + east_m / (111_320 * max(0.1, math.cos(math.radians(lat))))
    return lat2, lon2


def scenario_state(t_seconds):
    door_open = t_seconds == 120
    shock_event = t_seconds == 270
    stopped = 400 <= t_seconds < 520
    is_deviated = 500 <= t_seconds < 580
    events = []
    if door_open:
        events.append({"code": "SUSPICIOUS_DOOR_OPEN", "label": "Ouverture de porte suspecte"})
    if shock_event:
        events.append({"code": "ABNORMAL_SHOCK", "label": "Secousse / Choc anormal"})
    if stopped:
        events.append({"code": "UNPLANNED_STOP", "label": "Arrêt prolongé non planifié"})
    if is_deviated:
        events.append({"code": "ROUTE_DEVIATION", "label": "Décalage de route / Sortie d'itinéraire"})
    speed_kmh = 0.0 if stopped else 55.0 + 4.0 * math.sin(t_seconds / 17)
    return {
        "door_open": door_open,
        "shock_event": shock_event,
        "stopped": stopped,
        "is_deviated": is_deviated,
        "speed_kmh": round(speed_kmh, 1),
        "events": events,
        "event_code": ",".join(event["code"] for event in events),
        "event": " · ".join(event["label"] for event in events),
    }


def telemetry_payload(args, t_seconds, started_monotonic):
    lat, lon, heading = _route_point(t_seconds / (DURATION_SECONDS - 1))
    state = scenario_state(t_seconds)
    if state["is_deviated"]:
        lat, lon = _offset_lateral(lat, lon, heading, DEVIATION_METERS)

    shock_g = 12.0 if state["shock_event"] else round(random.uniform(0.05, 0.35), 2)
    scenario_id = f"douala-yaounde-bertoua-{int(started_monotonic * 1_000_000)}"
    return {
        "messageId": str(uuid.uuid4()),
        "type": "telemetry",
        "deviceUid": args.device_uid,
        "blackBoxId": args.black_box_id,
        "containerId": args.container_id,
        "timestamp": _utc_now(),
        "sequence": args.start_sequence + t_seconds,
        "position": {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "accuracy": 8.0,
            "speed": state["speed_kmh"],
            "heading": round(heading, 1),
            "source": "ARGOS_SIMULATOR",
        },
        "sensors": {
            "temperature": 28.0,
            "humidity": 68.0,
            "shock": shock_g,
            "pressure": 1013.0,
            "flameDetected": False,
            "doorOpen": state["door_open"],
            "batteryLevel": 96.0,
            "lightLevel": 1200,
            "soundLevel": 350,
            "distanceCm": 40.0,
            "accelerationX": 12.0 if state["shock_event"] else 0.1,
            "accelerationY": 10.0 if state["shock_event"] else -0.1,
            "accelerationZ": 18.0 if state["shock_event"] else 9.8,
            "securityAlarm": False,
        },
        "modes": {
            "securityEnabled": True,
            "audioRecordingEnabled": False,
            "audioListeningEnabled": False,
            "flameDetectionEnabled": False,
        },
        "quality": {
            "dhtValid": True,
            "mpuValid": True,
            "gpsValid": True,
            "distanceValid": True,
            "sdReady": False,
            "pressureMeasured": False,
            "batteryMeasured": False,
            "timestampSource": "SIMULATION",
            "dataOrigin": "SYNTHETIC",
            "datasetId": scenario_id,
            "scenarioId": "douala-yaounde-bertoua",
            "sampleLabel": "simulation temporelle; données synthétiques",
        },
        "scenario": {
            "simulation_id": scenario_id,
            "t_seconds": t_seconds,
            "event_code": state["event_code"],
            "event": state["event"],
            "events": state["events"],
            "door_open": state["door_open"],
            "shock_event": state["shock_event"],
            "stopped": state["stopped"],
            "is_deviated": state["is_deviated"],
            "speed_kmh": state["speed_kmh"],
        },
    }


def _default_sequence_state_path():
    state_root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_root / "argos" / "simulator_sequences.json"


def _reserve_start_sequence(device_uid, state_path=None, requested_start=None):
    """Reserve a unique monotonic sequence range so every run can restart at t=0."""
    path = Path(state_path) if state_path else _default_sequence_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            try:
                state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            except (OSError, json.JSONDecodeError):
                state = {}
            if not isinstance(state, dict):
                state = {}
            last_reserved = int(state.get(device_uid, 0) or 0)
            if requested_start is None:
                start = max(time.time_ns() // 1_000, last_reserved + 1)
            else:
                start = int(requested_start)
                if start <= last_reserved:
                    raise ValueError(
                        f"--start-sequence {start} n'est pas supérieur à la dernière plage réservée "
                        f"({last_reserved}); retirez cette option pour l'attribution automatique."
                    )
            state[device_uid] = start + SEQUENCE_RESERVATION_SIZE - 1
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
            ) as state_file:
                json.dump(state, state_file, ensure_ascii=False, sort_keys=True)
                state_file.write("\n")
                state_file.flush()
                os.fsync(state_file.fileno())
                temp_path = Path(state_file.name)
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, path)
            return start
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _send_worker(args, outbox, headers):
    session = requests.Session()
    url = f"{args.base_url.rstrip('/')}/api/iot/telemetry"
    while True:
        item = outbox.get()
        try:
            if item is None:
                return
            for attempt in range(3):
                try:
                    response = session.post(url, json=item, headers=headers, timeout=8)
                    if response.status_code >= 500 or response.status_code == 429:
                        response.raise_for_status()
                    if response.status_code >= 400:
                        print(f"[{item['sequence']}] HTTP {response.status_code}: {response.text[:300]}",
                              flush=True)
                    else:
                        print(f"[{item['sequence']}] envoyé — HTTP {response.status_code}", flush=True)
                    break
                except requests.RequestException as exc:
                    if attempt == 2:
                        print(f"[{item['sequence']}] échec après 3 essais: {exc}", flush=True)
                    else:
                        time.sleep(0.25 * (2 ** attempt))
        finally:
            outbox.task_done()


def cmd_simulate_route(args):
    args.start_sequence = _reserve_start_sequence(
        args.device_uid,
        state_path=getattr(args, "sequence_state_file", None),
        requested_start=args.start_sequence,
    )
    headers = {"X-Device-Key": args.api_key}
    outbox = queue.Queue()  # non bornée pour ne jamais ralentir/abandonner la simulation
    worker = threading.Thread(target=_send_worker, args=(args, outbox, headers),
                              name="argos-telemetry-uploader", daemon=True)
    worker.start()
    started = time.monotonic()
    print("Simulation Douala → Yaoundé → Bertoua : 600 points à 1 Hz", flush=True)
    print(f"Séquences réservées : {args.start_sequence}–{args.start_sequence + DURATION_SECONDS - 1}", flush=True)
    print("Nouvelle exécution : départ du scénario à Douala (t=0).", flush=True)
    print("Point vert normal; déviation rouge; données marquées SYNTHETIC.", flush=True)
    try:
        for t_seconds in range(DURATION_SECONDS):
            deadline = started + t_seconds
            delay = deadline - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            payload = telemetry_payload(args, t_seconds, started)
            outbox.put(payload)
            if t_seconds in {120, 270, 400, 500, 520, 580}:
                if payload["scenario"]["event"]:
                    print(f"t={t_seconds:03d}s {payload['scenario']['event']}", flush=True)
                elif t_seconds in {520, 580}:
                    print(f"t={t_seconds:03d}s fin d'un événement de scénario", flush=True)
        print("600 trames générées; vidage de la file d'envoi...", flush=True)
        outbox.join()
    except KeyboardInterrupt:
        print("Interruption demandée; envoi des trames déjà en file...", flush=True)
        outbox.join()
    finally:
        outbox.put(None)
        worker.join(timeout=10)


def cmd_ack(args):
    payload = {
        "commandUid": args.command_uid,
        "deviceUid": args.device_uid,
        "status": args.status,
        "timestamp": _utc_now(),
        "result": json.loads(args.result),
    }
    post_json(args.base_url, "/api/iot/acknowledgements", payload,
              {"X-Device-Key": args.api_key})


def build_parser():
    parser = argparse.ArgumentParser(description="Simulateur IoT ARGOS")
    parser.add_argument("--base-url", default="http://127.0.0.1:5002",
                        help="URL du backend ARGOS")
    sub = parser.add_subparsers(required=True)

    provision = sub.add_parser("provision", help="Préparer un appareil dans ARGOS")
    provision.add_argument("--black-box-id", type=int, required=True)
    provision.add_argument("--hardware-serial", default=f"SIM-{uuid.uuid4().hex[:8].upper()}")
    provision.add_argument("--firmware-version", default="sim-2.0.0")
    provision.add_argument("--username", required=True)
    provision.add_argument("--password", required=True)
    provision.set_defaults(func=cmd_provision)

    enroll = sub.add_parser("enroll", help="Enrôler un appareil provisionné")
    enroll.add_argument("--device-uid", required=True)
    enroll.add_argument("--token", required=True)
    enroll.set_defaults(func=cmd_enroll)

    simulate = sub.add_parser("simulate-route", aliases=["telemetry"],
                              help="Simuler le trajet de 10 minutes, 1 point/s")
    simulate.add_argument("--device-uid", required=True)
    simulate.add_argument("--api-key", required=True)
    simulate.add_argument("--black-box-id", type=int, required=True)
    simulate.add_argument("--container-id", required=True)
    simulate.add_argument("--start-sequence", type=int, default=None,
                          help="Début explicite (normalement attribué automatiquement à chaque lancement)")
    simulate.add_argument("--sequence-state-file", default=None,
                          help="Fichier d'état des séquences; défaut: ~/.local/state/argos/simulator_sequences.json")
    simulate.set_defaults(func=cmd_simulate_route)

    ack = sub.add_parser("ack", help="Accuser réception d'une commande appareil")
    ack.add_argument("--device-uid", required=True)
    ack.add_argument("--api-key", required=True)
    ack.add_argument("--command-uid", required=True)
    ack.add_argument("--status", default="SUCCEEDED")
    ack.add_argument("--result", default="{}")
    ack.set_defaults(func=cmd_ack)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    parsed.func(parsed)
