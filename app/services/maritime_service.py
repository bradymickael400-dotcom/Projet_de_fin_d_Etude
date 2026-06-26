"""Service de tracking maritime avec adaptateurs provider."""
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import requests


class MaritimeTrackingAdapter(ABC):
    @abstractmethod
    def get_vessel_position(self, imo: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_vessel_position_at(self, imo: str, target_ts: datetime) -> Optional[dict]:
        pass

    @abstractmethod
    def get_container_tracking(self, container_number: str, bl_number: str = None) -> Optional[dict]:
        pass


class VizionAdapter(MaritimeTrackingAdapter):
    BASE_URL = "https://go.vizionapi.com/v2"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key, "Content-Type": "application/json"})

    def get_vessel_position(self, imo: str) -> Optional[dict]:
        return None

    def get_vessel_position_at(self, imo: str, target_ts: datetime) -> Optional[dict]:
        return None

    def get_container_tracking(self, container_number: str, bl_number: str = None) -> Optional[dict]:
        try:
            payload = {"container_number": container_number.upper()}
            if bl_number:
                payload["bill_of_lading"] = bl_number
            resp = self.session.post(f"{self.BASE_URL}/tracking", json=payload, timeout=20)
            if resp.status_code not in (200, 201, 409):
                resp.raise_for_status()
            tracking_id = resp.json().get("id") or resp.json().get("tracking_id")
            if not tracking_id:
                return None
            resp2 = self.session.get(f"{self.BASE_URL}/tracking/{tracking_id}", timeout=20)
            resp2.raise_for_status()
            return self._normalize_vizion_response(container_number, resp2.json())
        except requests.exceptions.RequestException as e:
            print(f"[VIZION ERROR] {e}")
            return None

    def _normalize_vizion_response(self, container_number: str, raw: dict) -> dict:
        vessel = raw.get("vessel") or {}
        events = []
        for ev in raw.get("events") or []:
            location = ev.get("location") or {}
            events.append({
                "ts": ev.get("timestamp"),
                "location": location.get("name"),
                "locode": location.get("locode"),
                "description": ev.get("description") or ev.get("event_type"),
                "lat": location.get("lat"),
                "lon": location.get("lon"),
            })
        return {
            "container_number": container_number,
            "status": raw.get("status", "unknown"),
            "pol": (raw.get("pol") or {}).get("locode"),
            "pod": (raw.get("pod") or {}).get("locode"),
            "eta": raw.get("eta"),
            "vessel_imo": vessel.get("imo"),
            "vessel_name": vessel.get("name"),
            "events": events,
            "tracking_id": raw.get("id"),
            "provider": "vizion",
        }


class MarineTrafficAdapter(MaritimeTrackingAdapter):
    BASE_URL = "https://services.marinetraffic.com/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str, params: dict) -> Optional[dict]:
        params.update({"v": 8, "msgtype": "json", "USERKEY": self.api_key})
        try:
            resp = requests.get(f"{self.BASE_URL}/{path}", params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[MARINETRAFFIC ERROR] {e}")
            return None

    def get_vessel_position(self, imo: str) -> Optional[dict]:
        raw = self._get("exportvessel/8", {"IMO": imo, "protocol": "jsono"})
        if not raw or not raw.get("DATA"):
            return None
        vessel_data = raw["DATA"][0]
        return {
            "imo": imo,
            "lat": float(vessel_data.get("LAT", 0)),
            "lon": float(vessel_data.get("LON", 0)),
            "speed_knots": float(vessel_data.get("SPEED", 0)) / 10,
            "heading_deg": vessel_data.get("HEADING"),
            "nav_status": vessel_data.get("NAVSTAT"),
            "ts": vessel_data.get("TIMESTAMP"),
            "vessel_name": vessel_data.get("SHIPNAME"),
            "source": "marinetraffic",
        }

    def get_vessel_position_at(self, imo: str, target_ts: datetime) -> Optional[dict]:
        raw = self._get("getvessel/8", {
            "IMO": imo,
            "FROMDATE": target_ts.strftime("%Y-%m-%d %H:%M"),
            "TODATE": target_ts.strftime("%Y-%m-%d %H:%M"),
        })
        if not raw or not raw.get("DATA"):
            return None
        target_epoch = target_ts.timestamp()
        closest = min(raw["DATA"], key=lambda p: abs(datetime.fromisoformat(p["TIMESTAMP"]).timestamp() - target_epoch))
        return {
            "imo": imo,
            "lat": float(closest.get("LAT", 0)),
            "lon": float(closest.get("LON", 0)),
            "speed_knots": float(closest.get("SPEED", 0)) / 10,
            "ts": closest.get("TIMESTAMP"),
            "source": "marinetraffic_historical",
        }

    def get_container_tracking(self, container_number: str, bl_number: str = None) -> Optional[dict]:
        return None


def get_maritime_adapter() -> MaritimeTrackingAdapter:
    provider = os.getenv("MARITIME_PROVIDER", "vizion").lower()
    if provider == "vizion":
        key = os.getenv("VIZION_API_KEY", "")
        if not key:
            raise EnvironmentError("VIZION_API_KEY manquant dans .env")
        return VizionAdapter(key)
    if provider == "marinetraffic":
        key = os.getenv("MT_API_KEY", "")
        if not key:
            raise EnvironmentError("MT_API_KEY manquant dans .env")
        return MarineTrafficAdapter(key)
    raise ValueError(f"Provider maritime inconnu : {provider}")
