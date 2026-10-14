#!/usr/bin/env python3
"""Simulateur ESP32 pour le flux backend IoT ARGOS.

Exemples:
  python simulateur_iot.py provision --black-box-id 1
  python simulateur_iot.py enroll --device-uid ARGOS-ESP32-ABCD1234 --token TOKEN
  python simulateur_iot.py telemetry --device-uid ARGOS-ESP32-ABCD1234 --container-id MSCU1234566 --api-key KEY
  python simulateur_iot.py ack --device-uid ARGOS-ESP32-ABCD1234 --api-key KEY --command-uid UUID --status SUCCEEDED
"""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone

import requests


def post_json(base_url, path, payload, headers=None):
    response = requests.post(
        f"{base_url.rstrip('/')}{path}",
        json=payload,
        headers=headers or {},
        timeout=15,
    )
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    print(json.dumps({"status_code": response.status_code, "body": body}, indent=2, ensure_ascii=False))
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
    headers = {"Authorization": f"Bearer {access_token}"}
    post_json(args.base_url, "/api/iot/devices/provision", payload, headers)


def cmd_enroll(args):
    payload = {"deviceUid": args.device_uid, "enrollmentToken": args.token}
    post_json(args.base_url, "/api/iot/enroll", payload)


def telemetry_payload(device_uid, container_id, sequence, lat, lon):
    return {
        "messageId": str(uuid.uuid4()),
        "deviceUid": device_uid,
        "containerId": container_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
        "type": "telemetry",
        "position": {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "accuracy": 8,
            "speed": round(random.uniform(0, 80), 1),
            "heading": round(random.uniform(0, 359), 1),
        },
        "sensors": {
            "temperature": round(random.uniform(18, 38), 1),
            "humidity": round(random.uniform(35, 90), 1),
            "shock": round(random.choice([0, 0.2, 0.8, random.uniform(2, 8)]), 2),
            "pressure": round(random.uniform(985, 1025), 1),
            "flameDetected": random.random() < 0.03,
            "doorOpen": random.random() < 0.05,
            "batteryLevel": round(random.uniform(40, 100), 1),
            "lightLevel": random.randint(0, 4095),
            "soundLevel": random.randint(0, 4095),
            "distanceCm": round(random.uniform(5, 120), 1),
            "accelerationX": round(random.uniform(-2, 2), 2),
            "accelerationY": round(random.uniform(-2, 2), 2),
            "accelerationZ": round(random.uniform(8, 12), 2),
            "securityAlarm": False,
        },
        "modes": {
            "securityEnabled": False,
            "audioRecordingEnabled": False,
            "audioListeningEnabled": False,
            "flameDetectionEnabled": True,
        },
    }


def cmd_telemetry(args):
    headers = {"X-Device-Key": args.api_key}
    lat = args.lat
    lon = args.lon
    for sequence in range(args.start_sequence, args.start_sequence + args.count):
        lat += random.uniform(-0.002, 0.002)
        lon += random.uniform(-0.002, 0.002)
        payload = telemetry_payload(args.device_uid, args.container_id, sequence, lat, lon)
        payload["sensors"]["securityAlarm"] = payload["sensors"]["distanceCm"] > args.distance_threshold
        post_json(args.base_url, "/api/iot/telemetry", payload, headers)
        if sequence < args.start_sequence + args.count - 1:
            time.sleep(args.interval)


def cmd_ack(args):
    payload = {
        "commandUid": args.command_uid,
        "deviceUid": args.device_uid,
        "status": args.status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": json.loads(args.result),
    }
    headers = {"X-Device-Key": args.api_key}
    post_json(args.base_url, "/api/iot/acknowledgements", payload, headers)


def build_parser():
    parser = argparse.ArgumentParser(description="Simulateur ESP32 ARGOS")
    parser.add_argument("--base-url", default="http://127.0.0.1:5002")
    sub = parser.add_subparsers(required=True)

    provision = sub.add_parser("provision")
    provision.add_argument("--black-box-id", type=int)
    provision.add_argument("--hardware-serial", default=f"SIM-{uuid.uuid4().hex[:8].upper()}")
    provision.add_argument("--firmware-version", default="sim-1.0.0")
    provision.add_argument("--username", required=True)
    provision.add_argument("--password", required=True)
    provision.set_defaults(func=cmd_provision)

    enroll = sub.add_parser("enroll")
    enroll.add_argument("--device-uid", required=True)
    enroll.add_argument("--token", required=True)
    enroll.set_defaults(func=cmd_enroll)

    telemetry = sub.add_parser("telemetry")
    telemetry.add_argument("--device-uid", required=True)
    telemetry.add_argument("--api-key", required=True)
    telemetry.add_argument("--container-id", required=True)
    telemetry.add_argument("--distance-threshold", type=float, default=50.0)
    telemetry.add_argument("--count", type=int, default=1)
    telemetry.add_argument("--interval", type=float, default=2)
    telemetry.add_argument("--start-sequence", type=int, default=1)
    telemetry.add_argument("--lat", type=float, default=4.0511)
    telemetry.add_argument("--lon", type=float, default=9.7679)
    telemetry.set_defaults(func=cmd_telemetry)

    ack = sub.add_parser("ack")
    ack.add_argument("--device-uid", required=True)
    ack.add_argument("--api-key", required=True)
    ack.add_argument("--command-uid", required=True)
    ack.add_argument("--status", default="SUCCEEDED")
    ack.add_argument("--result", default="{}")
    ack.set_defaults(func=cmd_ack)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
