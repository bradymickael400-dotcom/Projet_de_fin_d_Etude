#!/usr/bin/env python3
"""Simulateur de télémétrie pour 5 boîtes noires pendant 30 minutes.

Ce script envoie des paquets de données réguliers à l'endpoint
/api/telemetry sur le serveur local (par défaut http://127.0.0.1:5002).
Il génère des mouvements GPS, des vitesses réalistes et des valeurs de capteurs
pour simuler un transport en temps réel.
"""

import argparse
import json
import math
import random
import time

try:
    import requests
except ImportError:
    raise SystemExit("Le module requests est requis. Installez-le avec pip install requests.")

DEFAULT_URL = "http://127.0.0.1:5002/api/telemetry"
DEFAULT_DURATION_MIN = 30
DEFAULT_INTERVAL_SEC = 30
DEFAULT_BOXES = [1, 2, 3, 4, 5]

START_COORDS = [
    (4.05, 9.70),
    (4.85, 10.93),
    (3.98, 11.45),
    (4.20, 10.35),
    (4.45, 10.80),
]


def move(lat, lon, heading, speed, interval_sec):
    """Déplace un point GPS selon une vitesse et une direction.
    La formule est approximative et convient pour de courtes distances.
    """
    distance_km = speed * (interval_sec / 3600.0)
    km_per_deg = 111.0
    delta_deg = distance_km / km_per_deg
    rad = math.radians(heading)
    new_lat = lat + delta_deg * math.cos(rad)
    new_lon = lon + delta_deg * math.sin(rad) / max(0.3, math.cos(math.radians(lat)))
    return new_lat, new_lon


def build_payload(box_id, lat, lon):
    speed = max(0.0, min(120.0, random.gauss(55.0, 18.0)))
    temperature = min(max(round(random.gauss(30.5, 3.8), 1), 18.0), 42.0)
    humidite = min(max(round(random.gauss(64.0, 8.5), 1), 30.0), 92.0)
    pressions = min(max(round(random.gauss(1002.0, 7.0), 1), 965.0), 1018.0)
    chocs = round(abs(random.gauss(1.2, 1.9)), 1)

    if random.random() < 0.12:
        temperature = min(48.0, temperature + random.uniform(3.5, 8.0))
    if random.random() < 0.09:
        chocs += random.uniform(1.0, 5.5)
    if random.random() < 0.08:
        speed += random.uniform(12.0, 28.0)
    if random.random() < 0.07:
        humidite = min(100.0, humidite + random.uniform(8.0, 16.0))
    if random.random() < 0.06:
        pressions = max(950.0, pressions - random.uniform(10.0, 18.0))

    return {
        "id_boite": box_id,
        "temperature": temperature,
        "humidite": humidite,
        "pressions": pressions,
        "chocs": chocs,
        "vitesse": round(min(max(speed, 0.0), 130.0), 1),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
    }


def simulate(url, duration_min, interval_sec, box_ids):
    if len(box_ids) != len(START_COORDS):
        raise ValueError("La liste de boîtes doit avoir une coordonnée de départ par boîte.")

    boxes = [
        {
            "id": box_id,
            "lat": START_COORDS[idx][0],
            "lon": START_COORDS[idx][1],
            "heading": random.uniform(0, 360),
        }
        for idx, box_id in enumerate(box_ids)
    ]

    total_steps = int(duration_min * 60 / interval_sec)
    print(f"Simulateur IoT : {len(box_ids)} boîtes sur {duration_min} minutes ({total_steps} envois par boîte)")
    print(f"Endpoint : {url}")
    print("=" * 72)

    for step in range(1, total_steps + 1):
        for box in boxes:
            box["heading"] = (box["heading"] + random.uniform(-18.0, 18.0)) % 360
            payload = build_payload(box["id"], box["lat"], box["lon"])
            box["lat"], box["lon"] = move(box["lat"], box["lon"], box["heading"], payload["vitesse"], interval_sec)

            try:
                resp = requests.post(url, json=payload, timeout=15)
                text = resp.text.strip()
                if resp.status_code == 201:
                    data = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
                    alerts = data.get("alertes_declenchees") or data.get("alertes") or []
                    if alerts:
                        print(f"[{step}/{total_steps}] Boîte {box['id']} → ALERTES={len(alerts)} vitesse={payload['vitesse']} km/h loc=({payload['lat']},{payload['lon']})")
                    else:
                        print(f"[{step}/{total_steps}] Boîte {box['id']} → OK vitesse={payload['vitesse']} km/h loc=({payload['lat']},{payload['lon']})")
                else:
                    print(f"[{step}/{total_steps}] Boîte {box['id']} → ERREUR {resp.status_code} : {text}")
            except requests.RequestException as exc:
                print(f"[{step}/{total_steps}] Boîte {box['id']} → ERREUR REQUÊTE : {exc}")

        if step < total_steps:
            time.sleep(interval_sec)

    print("=" * 72)
    print("Simulation terminée.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur de télémétrie pour 5 boîtes pendant 30 minutes.")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL de l'endpoint de télémétrie")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_MIN, help="Durée de simulation en minutes")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SEC, help="Intervalle entre envois en secondes")
    parser.add_argument("--boxes", nargs="*", type=int, default=DEFAULT_BOXES, help="Liste d'identifiants de boîtes à simuler")
    args = parser.parse_args()

    simulate(args.url, args.duration, args.interval, args.boxes)
