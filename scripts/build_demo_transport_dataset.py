#!/usr/bin/env python3
"""Build a deterministic one-hour, two-route ARGOS demo batch (synthetic only)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "datasets" / "argos_demo_two_routes.json"


def iso6346(prefix, serial):
    values = {chr(letter): value for letter, value in zip(range(65, 91),
        [10,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,30,31,32,34,35,36,37,38])}
    body = prefix + serial
    total = sum(((values[char] if char in values else int(char)) * (2 ** index)
                 for index, char in enumerate(body)))
    check = (total % 11) % 10
    return f"{body}{check}"


def interpolate(points, fraction):
    lengths = []
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        lengths.append(((lat2-lat1)**2 + (lon2-lon1)**2) ** 0.5)
    total = sum(lengths) or 1
    target = max(0, min(1, fraction)) * total
    for index, length in enumerate(lengths):
        if target <= length or index == len(lengths)-1:
            ratio = target / (length or 1)
            a, b = points[index], points[index+1]
            return [round(a[0] + (b[0]-a[0])*ratio, 6), round(a[1] + (b[1]-a[1])*ratio, 6)]
        target -= length
    return list(points[-1])


START = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def scenario(case_id, mode, origin, destination, container, driver, threshold, route, window_route,
             shock_events, speed_events, door_window, stop_window, stop_point, zones):
    points = []
    for minute in range(60):
        progress = minute / 59
        latlon = interpolate(window_route, progress)
        if stop_window[0] <= minute <= stop_window[1]:
            latlon = list(stop_point)
        speed = (0 if stop_window[0] <= minute <= stop_window[1] else
                 speed_events.get(minute, 34 if mode == "sea" else 62))
        shock = shock_events.get(minute, 0.08 if minute % 7 else 0.15)
        door_open = door_window[0] <= minute <= door_window[1]
        points.append({
            "minute": minute,
            "timestamp": (START + timedelta(minutes=minute)).isoformat(),
            "position": {"latitude": latlon[0], "longitude": latlon[1], "speed_kmh": speed,
                         "heading_deg": 90 if mode == "sea" else 315, "accuracy_m": 8},
            "sensors": {"temperature_c": 22.5 if mode == "sea" else 26.2,
                        "humidity_percent": 61.0, "shock_g": shock,
                        "door_open": door_open, "security_alarm": door_open and minute == door_window[0],
                        "pressure_hpa": 1008.0, "battery_percent": 98 - minute // 20},
            "event": ("stable" if minute not in shock_events and minute not in speed_events
                      and not door_open and not (stop_window[0] <= minute <= stop_window[1])
                      else "simulated_anomaly"),
            "zone_transition_expected": next((zone["id"] for zone in zones
                if zone.get("enter_minute") == minute), None),
        })
    threshold = dict(threshold)
    return {
        "scenario_id": case_id,
        "synthetic": True,
        "mode": mode,
        "route": {"origin": origin, "destination": destination, "waypoints": route,
                  "simulation_window_minutes": 60,
                  "window_note": "Première heure simulée du trajet; elle ne représente pas la durée complète du voyage.",
                  "playback_mode": "one_sample_per_minute"},
        "provisioning": {
            "company": {"name": "ARGOS Transport Démo", "niu": f"DEMO-{case_id.upper()}-NIU",
                        "login": f"demo.company.{case_id}", "email": "demo-company@example.invalid",
                        "password_placeholder": "À définir hors de ce fichier"},
            "driver": {"id_cni": f"DEMO-{case_id.upper()}-DRIVER", "first_name": driver[0],
                       "last_name": driver[1], "login": f"demo.driver.{case_id}",
                       "contact": "+237600000000", "password_placeholder": "À définir hors de ce fichier"},
            "container": {"container_number": container, "classification": "synthetic demo",
                          "company_link_required": True},
            "black_box": {"serial": f"ARGOS-DEMO-{case_id.upper()}", "type": "continuous",
                          "deployment_date": START.isoformat(), "firmware": "v2.1-demo",
                          "initial_parameters": threshold, "initial_route": route,
                          "driver_affiliation": "link driver to the created company and shipment"},
            "journey": {"mode": mode, "from": origin, "to": destination,
                        "assign_driver": True, "assign_company": True,
                        "assign_container_and_black_box": True},
        },
        "geofences": zones,
        "expected_incidents": {
            "speed_exceedance_minutes": sorted(speed_events),
            "shock_event_minutes": sorted(shock_events),
            "shock_count": len(shock_events),
            "shock_sum_g": round(sum(shock_events.values()), 2),
            "door_open_minutes": list(range(door_window[0], door_window[1]+1)),
            "stationary_minutes": list(range(stop_window[0], stop_window[1]+1)),
            "stationary_zone": next((z["name"] for z in zones if z.get("stop_zone")), None),
        },
        "samples": points,
    }


def main():
    scenarios = [
        scenario("china_cameroon", "sea", "Shanghai, Chine", "Douala, Cameroun",
            iso6346("ARGU", "000001"), ("Conducteur", "Démo Mer"),
            {"shock_max_g": 3.0, "speed_max_kmh": 55, "temperature_min_c": -10,
             "temperature_max_c": 32, "humidity_max_percent": 75, "door_open_alert": True},
            [["Shanghai",31.2304,121.4737],["Singapour",1.2903,103.8519],
             ["Colombo",6.9271,79.8612],["Suez",29.9668,32.5498],
             ["Gibraltar",36.1408,-5.3536],["Douala",4.0511,9.7679]],
            [[31.18,121.40],[31.28,121.54],[31.38,121.63]],
            {25:3.4,26:4.1,27:3.6}, {}, (37,38), (45,52), [31.36,121.59],
            [{"id":"CN_SHANGHAI_PORT","name":"Port de Shanghai — périmètre de démonstration","enter_minute":2},
             {"id":"SG_STRAIT","name":"Détroit de Singapour — périmètre de démonstration","enter_minute":None},
             {"id":"CM_DOUALA_PORT","name":"Port de Douala — périmètre de démonstration","enter_minute":None}]),
        scenario("bertoua_yaounde", "road", "Bertoua, Cameroun", "Yaoundé, Cameroun",
            iso6346("ARGU", "000002"), ("Conducteur", "Démo Route"),
            {"shock_max_g": 3.0, "speed_max_kmh": 80, "temperature_min_c": -10,
             "temperature_max_c": 32, "humidity_max_percent": 75, "door_open_alert": True},
            [["Bertoua",4.5770,13.6846],["Dimako",4.3830,13.5900],
             ["Abong-Mbang",3.9830,13.1830],["Ayos",3.9000,12.5160],
             ["Awaé",3.8330,11.6830],["Yaoundé",3.8480,11.5021]],
            [[4.5770,13.6846],[4.5350,13.6550],[4.4950,13.6250]],
            {18:94,19:101,20:97,21:92}, {30:3.5,31:4.2,32:5.1,33:3.8},
            (37,39), (45,52), [4.5200,13.6450],
            [{"id":"CM_BERTOUA","name":"Bertoua — zone urbaine de démonstration","enter_minute":0},
             {"id":"CM_N10_BERTOUA_DIMAKO","name":"Périmètre simulé N10 — secteur Bertoua–Dimako","enter_minute":15,
              "stop_zone":True},
             {"id":"CM_ABONG_MBANG","name":"Abong-Mbang — zone urbaine de démonstration","enter_minute":None},
             {"id":"CM_AYOS","name":"Ayos — zone urbaine de démonstration","enter_minute":None},
             {"id":"CM_YAOUNDE","name":"Yaoundé — zone urbaine de démonstration","enter_minute":None}]),
    ]
    batch = {
        "dataset_id": "ARGOS-DEMO-TRANSPORT-2ROUTES-v1",
        "synthetic": True,
        "description": "Deux trajets de démonstration avec une heure de mesures minute par minute, incluant périodes stables et incidents simulés.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_safety": "Les entreprises, chauffeurs, identifiants, valeurs et incidents sont fictifs. Les e-mails utilisent example.invalid. Le trajet complet n'est pas parcouru en une heure.",
        "provisioning_order": ["company", "driver", "container", "black_box", "thresholds", "shipment_and_route", "telemetry"],
        "normative_context": {"source_candidates": ["IMO_SOLAS_1974", "IMO_IMDG_CODE", "UN_CMR_1956", "CM_LAW_2001_015", "ARGOS_THRESHOLD_RULES"],
                              "applicability": "TO_VERIFY", "note": "Ne pas interpréter les seuils fictifs comme des limites légales."},
        "scenarios": scenarios,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Écrit {OUTPUT} ({sum(len(item['samples']) for item in scenarios)} mesures synthétiques)")


if __name__ == "__main__":
    main()
