"""
Service d'intégration BIC BoxTech API.
Standard : ISO 6346 - identification des conteneurs maritimes.
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests
from flask import current_app
from sqlalchemy import text

_ISO_LETTER_VALUES = {
    "A": 10, "B": 12, "C": 13, "D": 14, "E": 15, "F": 16, "G": 17,
    "H": 18, "I": 19, "J": 20, "K": 21, "L": 23, "M": 24, "N": 25,
    "O": 26, "P": 27, "Q": 28, "R": 29, "S": 30, "T": 31, "U": 32,
    "V": 34, "W": 35, "X": 36, "Y": 37, "Z": 38,
}


def validate_iso6346(container_id: str) -> Tuple[bool, str]:
    cid = (container_id or "").upper().replace(" ", "").replace("-", "")
    if len(cid) != 11:
        return False, f"Longueur invalide : {len(cid)} caractères (attendu 11)"

    owner_code = cid[:3]
    equip_cat = cid[3]
    serial = cid[4:10]
    check_digit = cid[10]

    if not re.match(r"^[A-Z]{3}$", owner_code):
        return False, f"Code propriétaire invalide : {owner_code}"
    if equip_cat not in ("U", "J", "Z"):
        return False, f"Catégorie équipement invalide : {equip_cat}"
    if not serial.isdigit():
        return False, f"Numéro série invalide : {serial}"

    total = 0
    for i, char in enumerate(cid[:10]):
        val = _ISO_LETTER_VALUES[char] if char.isalpha() else int(char)
        total += val * (2 ** i)

    remainder = total % 11
    expected_check = 0 if remainder == 10 else remainder
    if not check_digit.isdigit() or int(check_digit) != expected_check:
        return False, f"Chiffre de contrôle invalide : {check_digit} (calculé : {expected_check})"

    return True, "OK"


class BICBoxTechService:
    BASE_URL = "https://app.bic-boxtech.org"
    TOKEN_URL = f"{BASE_URL}/oauth/token"
    CONTAINER_URL = f"{BASE_URL}/api/v2.0/container"

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_credentials(self) -> Tuple[str, str]:
        client_id = current_app.config.get("BIC_CLIENT_ID", "")
        client_secret = current_app.config.get("BIC_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise ValueError("BIC_CLIENT_ID et BIC_CLIENT_SECRET requis dans .env")
        return client_id, client_secret

    def _ensure_token(self) -> str:
        now = datetime.utcnow()
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        client_id, client_secret = self._get_credentials()
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = now + timedelta(seconds=token_data.get("expires_in", 3600) - 60)
        return self._access_token

    def fetch_container_specs(self, container_number: str) -> Optional[dict]:
        valid, reason = validate_iso6346(container_number)
        if not valid:
            raise ValueError(f"Numéro ISO 6346 invalide : {reason}")

        cnum = container_number.upper().replace(" ", "").replace("-", "")
        token = self._ensure_token()
        resp = requests.get(
            f"{self.CONTAINER_URL}/{cnum}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._normalize_bic_response(cnum, resp.json())

    def _normalize_bic_response(self, container_number: str, raw: dict) -> dict:
        return {
            "container_number": container_number,
            "owner_prefix": container_number[:4],
            "type_code": raw.get("type_code") or raw.get("group_st"),
            "max_gross_mass_kg": raw.get("max_gross_weight"),
            "tare_mass_kg": raw.get("tare_weight"),
            "internal_length_mm": raw.get("internal_length"),
            "internal_width_mm": raw.get("internal_width"),
            "internal_height_mm": raw.get("internal_height"),
            "external_length_mm": raw.get("external_length"),
            "external_width_mm": raw.get("external_width"),
            "external_height_mm": raw.get("external_height"),
            "door_width_mm": raw.get("door_width"),
            "door_height_mm": raw.get("door_height"),
            "capacity_m3": raw.get("capacity"),
            "manufacture_year": raw.get("year_of_build") or raw.get("manufacture_year"),
            "bic_raw_response": json.dumps(raw),
        }

    def save_to_db(self, specs: dict) -> None:
        from app import db

        db.session.execute(text("""
            INSERT INTO bic_owner_prefix (prefix, company_name)
            VALUES (:owner_prefix, :owner_prefix)
            ON CONFLICT DO NOTHING
        """), specs)
        db.session.execute(text("""
            INSERT INTO container_specs_bic
                (container_number, owner_prefix, type_code, max_gross_mass_kg,
                 tare_mass_kg, internal_length_mm, internal_width_mm,
                 internal_height_mm, external_length_mm, external_width_mm,
                 external_height_mm, door_width_mm, door_height_mm,
                 capacity_m3, manufacture_year, bic_raw_response)
            VALUES
                (:container_number, :owner_prefix, :type_code, :max_gross_mass_kg,
                 :tare_mass_kg, :internal_length_mm, :internal_width_mm,
                 :internal_height_mm, :external_length_mm, :external_width_mm,
                 :external_height_mm, :door_width_mm, :door_height_mm,
                 :capacity_m3, :manufacture_year, CAST(:bic_raw_response AS jsonb))
            ON CONFLICT (container_number) DO UPDATE SET
                type_code = EXCLUDED.type_code,
                max_gross_mass_kg = EXCLUDED.max_gross_mass_kg,
                tare_mass_kg = EXCLUDED.tare_mass_kg,
                bic_fetch_ts = NOW(),
                bic_raw_response = EXCLUDED.bic_raw_response
        """), specs)
        db.session.commit()


_bic_service_instance: Optional[BICBoxTechService] = None


def get_bic_service() -> BICBoxTechService:
    global _bic_service_instance
    if _bic_service_instance is None:
        _bic_service_instance = BICBoxTechService()
    return _bic_service_instance
