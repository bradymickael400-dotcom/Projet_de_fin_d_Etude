#!/usr/bin/env python3
"""Create an isolated, owner-scoped ARGOS demo company, box and IoT device."""

import json
import os
import secrets
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATASET = ROOT / "datasets" / "argos_demo_two_routes.json"
ACCESS_FILE = ROOT / "private_documents" / "demo" / "argos_demo_access.json"
OWNER_LOGIN = "argos.demo.owner"
OWNER_NIU = "DEMO-ARGOS-TRANSPORT"
CONTAINER_ID = "ARGU0000012"
BOX_SERIAL = "ARGOS-DEMO-01"
DEVICE_UID = "ARGOS-ESP32-DEMO-TRANSPORT"


def _write_private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    load_dotenv(ROOT / ".env")
    from app import create_app
    from app.extensions import db
    from app.migrate import run_migrations

    run_migrations()
    app = create_app()
    batch = json.loads(DATASET.read_text(encoding="utf-8"))
    with app.app_context():
        owner = db.session.execute(text("""
            SELECT id,login,password FROM proprietaire_conteneur WHERE niu=:niu LIMIT 1
        """), {"niu": OWNER_NIU}).fetchone()
        if owner:
            owner_id = int(owner.id)
            password = secrets.token_urlsafe(18)
            db.session.execute(text("""
                UPDATE proprietaire_conteneur SET password=:password WHERE id=:id
            """), {"password": generate_password_hash(password), "id": owner_id})
        else:
            password = secrets.token_urlsafe(18)
            owner_id = db.session.execute(text("""
                INSERT INTO proprietaire_conteneur
                    (niu,nom_agence,login,password,addresse_mail,lieu_residence,nbr_boite)
                VALUES(:niu,'ARGOS Transport Démonstration',:login,:password,
                       'demo-company@example.invalid','Environnement local de démonstration',1)
                RETURNING id
            """), {"niu": OWNER_NIU, "login": OWNER_LOGIN,
                   "password": generate_password_hash(password)}).scalar()

        db.session.execute(text("""
            INSERT INTO conteneurs
                (id_conteneurs,taile_perimetre,type_conteneurs,status,technical_info,
                 bic_registered,local_only,bic_validation_msg,created_by)
            VALUES(:container,'40 pieds','DEMO SYNTHÉTIQUE','ok',
                   CAST(:info AS jsonb),FALSE,TRUE,
                   'Donnée synthétique ARGOS; identifiant de démonstration non revendiqué BIC.',
                   'setup_demo_transport')
            ON CONFLICT (id_conteneurs) DO UPDATE SET
                technical_info=EXCLUDED.technical_info,local_only=TRUE,
                bic_registered=FALSE,bic_validation_msg=EXCLUDED.bic_validation_msg
        """), {"container": CONTAINER_ID, "info": json.dumps({
            "synthetic": True, "dataset_id": batch["dataset_id"],
            "presentation_only": True, "port_scenario": "Douala",
        }, ensure_ascii=False)})
        box_id = db.session.execute(text("""
            SELECT id_boite FROM boite_noir WHERE numero_serie=:serial LIMIT 1
        """), {"serial": BOX_SERIAL}).scalar()
        if box_id:
            box_id = int(box_id)
            db.session.execute(text("""
                UPDATE boite_noir SET id_conteneurs=:container,id_proprietaire=:owner,
                    status='active',archived=FALSE,updated_at=NOW()
                WHERE id_boite=:box
            """), {"container": CONTAINER_ID, "owner": owner_id, "box": box_id})
        else:
            duration_type = db.session.execute(text("""
                SELECT data_type FROM information_schema.columns
                WHERE table_schema='brady' AND table_name='boite_noir'
                  AND column_name='expected_duration'
            """)).scalar()
            expected_duration = 365 if duration_type in {"integer", "smallint", "bigint"} else "365 jours"
            box_id = db.session.execute(text("""
                INSERT INTO boite_noir
                    (id_conteneurs,id_proprietaire,type_boite,versions,log_action,
                     deployment_date,battery_level,expected_duration,status,numero_serie)
                VALUES(:container,:owner,'continuous','v2.1-demo',
                       'Boîte de démonstration synthétique ARGOS',
                       NOW(),100,:duration,'active',:serial)
                RETURNING id_boite
            """), {"container": CONTAINER_ID, "owner": owner_id,
                   "duration": expected_duration, "serial": BOX_SERIAL}).scalar()
            box_id = int(box_id)

        db.session.execute(text("""
            INSERT INTO seuils_alerte
                (id_boite,temp_max,temp_min,humi_max,choc_max,pression_min,vitesse_max,angle_max)
            VALUES(:box,32,-10,75,3,995,80,30)
            ON CONFLICT(id_boite) DO UPDATE SET
                temp_max=EXCLUDED.temp_max,temp_min=EXCLUDED.temp_min,
                humi_max=EXCLUDED.humi_max,choc_max=EXCLUDED.choc_max,
                pression_min=EXCLUDED.pression_min,vitesse_max=EXCLUDED.vitesse_max,
                angle_max=EXCLUDED.angle_max
        """), {"box": box_id})
        db.session.commit()

        from app.modules.iot import repository as iot_repository
        iot_repository.ensure_iot_schema()
        device = db.session.execute(text("""
            SELECT d.id,d.device_uid,d.status,bbd.black_box_id
            FROM iot_devices d LEFT JOIN black_box_devices bbd
              ON bbd.device_id=d.id AND bbd.status='ACTIVE'
            WHERE d.device_uid=:uid ORDER BY d.id DESC LIMIT 1
        """), {"uid": DEVICE_UID}).fetchone()
        if device and str(device.status) == "ACTIVE" and int(device.black_box_id or 0) == box_id:
            device_uid = str(device.device_uid)
        else:
            if device and str(device.status) != "REVOKED":
                db.session.execute(text("""
                    UPDATE iot_devices SET status='REVOKED',revoked_at=NOW(),updated_at=NOW()
                    WHERE id=:id
                """), {"id": device.id})
                db.session.execute(text("""
                    UPDATE black_box_devices SET status='DETACHED',detached_at=NOW(),
                        reason='Reprovisionnement de la démo isolée'
                    WHERE device_id=:id AND status='ACTIVE'
                """), {"id": device.id})
                db.session.commit()
            from app.modules.iot.iot_service import enroll_device, provision_device
            fresh_uid = DEVICE_UID if not device else f"{DEVICE_UID}-{uuid.uuid4().hex[:6].upper()}"
            enrollment = provision_device({
                "device_uid": fresh_uid, "black_box_id": box_id,
                "hardware_serial": f"DEMO-{uuid.uuid4().hex[:10].upper()}",
                "firmware_version": "v2.1-demo",
            }, actor_role="owner", actor_id=owner_id)
            credentials = enroll_device({
                "deviceUid": enrollment["deviceUid"],
                "enrollmentToken": enrollment["enrollmentToken"],
            })
            device_uid = credentials["deviceUid"]

        from app.security import issue_access_token
        owner_row = db.session.execute(text("""
            SELECT login,nom_agence FROM proprietaire_conteneur WHERE id=:id
        """), {"id": owner_id}).fetchone()
        token = issue_access_token("owner", owner_id, owner_row.login, owner_row.nom_agence)
        access = {
            "synthetic": True,
            "warning": "Compte local de démonstration; ne pas utiliser en production.",
            "owner_login": owner_row.login,
            "password": password,
            "owner_id": owner_id,
            "access_token": token,
            "black_box_id": box_id,
            "black_box_serial": BOX_SERIAL,
            "container_id": CONTAINER_ID,
            "device_uid": device_uid,
            "dataset_id": batch["dataset_id"],
            "api_base_url": os.getenv(
                "DEMO_API_BASE_URL",
                f"http://127.0.0.1:{os.getenv('PORT','5003')}",
            ),
        }
        db.session.commit()
        _write_private_json(ACCESS_FILE, access)
        print(f"Boîte de démonstration prête: #{box_id}, conteneur {CONTAINER_ID}.")
        print(f"Compte propriétaire dédié: {owner_row.login} (mot de passe et jeton dans {ACCESS_FILE}).")
        print(f"Dispositif IoT actif: {device_uid}; toutes les données sont synthétiques.")


if __name__ == "__main__":
    main()
