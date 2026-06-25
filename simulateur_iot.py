#!/usr/bin/env python3
"""
Simulateur IoT simple : envoie des télémétries à /api/telemetry
Boucle pendant 30 minutes, envoie des données toutes les 10s pour chaque boîte.

Usage: python simulateur_iot.py --url http://127.0.0.1:5001 --ids 1 2 3

Le script tente de récupérer les boîtes actives depuis la base PostgreSQL si
les variables d'environnement PGHOST/PGUSER/PGPASSWORD/PGDATABASE sont renseignées.
Sinon il utilisera la liste statique passée via --ids.
"""
import time
import random
import argparse
import requests
import os
from datetime import datetime, timedelta

try:
    import psycopg2
except Exception:
    psycopg2 = None


def now():
    return datetime.now().strftime('%H:%M:%S')


def get_active_boites_from_db(limit=10):
    if not psycopg2:
        return []
    try:
        conn = psycopg2.connect(
            host=os.getenv('PGHOST','localhost'),
            user=os.getenv('PGUSER','postgres'),
            password=os.getenv('PGPASSWORD',''),
            dbname=os.getenv('PGDATABASE','argos')
        )
        cur = conn.cursor()
        # récupérer quelques boîtes récentes
        cur.execute("SELECT id_boite FROM boite_noir ORDER BY id_boite LIMIT %s", (limit,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Erreur DB: {e}")
        return []


def simulate_one_cycle(url, boite_id, state):
    # state contains last lat/lon
    lat, lon = state.get('lat'), state.get('lon')
    if lat is None or lon is None:
        # random start near central Africa
        lat = random.uniform(3.0, 6.0)
        lon = random.uniform(9.0, 12.0)

    # small movement
    lat += random.uniform(-0.001, 0.001)
    lon += random.uniform(-0.001, 0.001)

    temperature = round(random.uniform(-10, 40), 1)
    humidite = round(random.uniform(20, 90), 1)
    pression = round(random.uniform(980, 1035), 1)
    vitesse = round(random.uniform(0, 80), 1)
    chocs = round(random.choice([0, 0, 0, random.uniform(0.2, 6.0)]), 2)

    payload = {
        'id_boite': str(boite_id),
        'temperature': temperature,
        'humidite': humidite,
        'pressions': pression,
        'vitesse': vitesse,
        'chocs': chocs,
        'lat': lat,
        'lon': lon,
    }

    try:
        r = requests.post(url, json=payload, timeout=5)
        ok = r.status_code in (200,201)
        print(f"[{now()}] Boîte {boite_id}: Temp {temperature}°C, Humi {humidite}%, Choc {chocs}G -> {'OK' if ok else 'ERR('+str(r.status_code)+')'}")
    except Exception as e:
        print(f"[{now()}] Boîte {boite_id}: Erreur envoi -> {e}")

    state['lat'], state['lon'] = lat, lon


def main(url, ids, duration_minutes=30, interval_sec=10):
    # ids: list of boite ids (strings or ints)
    start = datetime.now()
    end = start + timedelta(minutes=duration_minutes)

    # state of each box
    states = {str(b): {'lat': None, 'lon': None} for b in ids}

    print(f"Simulateur démarré vers {url} — {len(ids)} boîtes — durée {duration_minutes} minutes")

    while datetime.now() < end:
        for b in ids:
            simulate_one_cycle(url, b, states[str(b)])
            time.sleep(0.2)  # léger étalement pour ne pas envoyer tout en même temps
        # attente jusqu'au prochain cycle
        remaining = interval_sec
        while remaining > 0:
            time.sleep(1)
            remaining -= 1

    print('Simulation terminée.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:5001/api/telemetry', help='URL de la route /api/telemetry')
    parser.add_argument('--ids', nargs='*', help='Liste d ids de boîtes (ex: 1 2 3)')
    parser.add_argument('--duration', type=int, default=30, help='Durée (minutes)')
    parser.add_argument('--interval', type=int, default=10, help='Intervalle entre envois (secondes)')
    args = parser.parse_args()

    ids = args.ids
    if not ids:
        # tenter de récupérer depuis la DB
        ids = get_active_boites_from_db(10)
    if not ids:
        # fallback statique
        ids = ['CONT-TEST-1','CONT-TEST-2']

    main(args.url, ids, duration_minutes=args.duration, interval_sec=args.interval)
