import argparse
import json
import math
import random
import time

import requests

URL = "http://127.0.0.1:5002/api/telemetry"

BOX_IDS = [1, 2, 3, 4, 5]

DEFAULT_DURATION_MIN = 30
DEFAULT_INTERVAL_SEC = 30

START_COORDS = [
    (4.05, 9.70),
    (4.85, 10.93),
    (3.98, 11.45),
    (4.20, 10.35),
    (4.45, 10.80)
]

THRESHOLDS = {
    "temperature": (28.0, 38.0),
    "humidite": (50.0, 85.0),
    "pressions": (985.0, 1015.0),
    "chocs": (0.0, 8.0),
    "vitesse": (0.0, 110.0),
}


def create_payload(box_id, lat, lon, heading):
    speed = max(0, min(110, random.gauss(60, 17)))
    temperature = round(random.gauss(30.5, 4.5), 1)
    humidite = round(random.gauss(65.0, 10.0), 1)
    pressions = round(random.gauss(1003.0, 8.0), 1)
    chocs = round(abs(random.gauss(1.5, 2.5)), 1)

    if random.random() < 0.12:
        temperature += random.uniform(3.5, 9.5)
    if random.random() < 0.1:
        chocs += random.uniform(1.0, 6.0)
    if random.random() < 0.08:
        speed += random.uniform(15.0, 35.0)
    if random.random() < 0.08:
        pressions -= random.uniform(12.0, 20.0)
    if random.random() < 0.08:
        humidite += random.uniform(10.0, 18.0)

    return {
        "id_boite": box_id,
        "temperature": round(min(max(temperature, 15.0), 45.0), 1),
        "humidite": round(min(max(humidite, 20.0), 95.0), 1),
        "pressions": round(min(max(pressions, 960.0), 1020.0), 1),
        "chocs": round(min(max(chocs, 0.0), 12.0), 1),
        "vitesse": round(min(max(speed, 0.0), 130.0), 1),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
    }


def move(lat, lon, heading, speed, interval_sec):
    km_per_deg = 111.0
    distance_km = speed * (interval_sec / 3600.0)
    delta_deg = distance_km / km_per_deg
    rad = math.radians(heading)
    new_lat = lat + delta_deg * math.cos(rad)
    new_lon = lon + delta_deg * math.sin(rad) / max(0.3, math.cos(math.radians(lat)))
    return new_lat, new_lon


def simulate(url, duration_min, interval_sec, box_ids):
    boxes = []
    for idx, box_id in enumerate(box_ids):
        heading = random.uniform(0, 360)
        boxes.append({
            "id": box_id,
            "lat": START_COORDS[idx][0],
            "lon": START_COORDS[idx][1],
            "heading": heading,
        })

    total_steps = int(duration_min * 60 / interval_sec)
    print(f"🚀 Simulation IoT: {len(box_ids)} boîtes sur {duration_min} minutes ({total_steps} envois par boîte)")
    print(f"URL cible : {url}")
    print("=" * 72)

    for step in range(1, total_steps + 1):
        for box in boxes:
            box["heading"] += random.uniform(-14.0, 14.0)
            box["heading"] %= 360
            payload = create_payload(box["id"], box["lat"], box["lon"], box["heading"])
            box["lat"], box["lon"] = move(box["lat"], box["lon"], box["heading"], payload["vitesse"], interval_sec)

            try:
                response = requests.post(url, json=payload, timeout=15)
                status = response.status_code
                data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}

                if status == 201:
                    alerts = data.get("alertes_declenchees") or data.get("alertes") or []
                    if alerts:
                        print(f"[{step}/{total_steps}] Boîte {box['id']} → ALERTES {len(alerts)} : {json.dumps(alerts)}")
                    else:
                        print(f"[{step}/{total_steps}] Boîte {box['id']} → OK | Vitesse={payload['vitesse']} km/h | Temp={payload['temperature']}°C")
                else:
                    print(f"[{step}/{total_steps}] Boîte {box['id']} → ERREUR {status} : {response.text}")
            except requests.exceptions.RequestException as exc:
                print(f"[{step}/{total_steps}] Boîte {box['id']} → ERREUR REQUÊTE : {exc}")

        if step < total_steps:
            time.sleep(interval_sec)

    print("=" * 72)
    print("✅ Simulation terminée. Vérifie maintenant les événements dans le dashboard et la table de télémétrie.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur de télémétrie IoT pour 5 boîtes sur 30 minutes.")
    parser.add_argument("--url", default=URL, help="URL de la route /api/telemetry")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_MIN, help="Durée de simulation en minutes")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SEC, help="Intervalle entre envois en secondes")
    parser.add_argument("--boxes", nargs="*", type=int, default=BOX_IDS, help="Liste d'id_boite à simuler")
    args = parser.parse_args()

    simulate(args.url, args.duration, args.interval, args.boxes)
