"""Worker fiable pour les tâches différées ARGOS."""

import json
import os
import time
import uuid

from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.services.report_service import generate_container_report_pdf
from app.services.storage_service import store_private_document


def _complete_job(job_id):
    db.session.execute(text("UPDATE background_jobs SET status='SUCCEEDED',updated_at=NOW() WHERE id=:id"), {"id": job_id})


def _process_revoke(job):
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload)
    db.session.execute(text("""
        UPDATE black_box_container_assignments SET status='ACCESS_REVOKED',visibility_until=NOW()
        WHERE black_box_id=:box AND container_id=:container AND status='DETACHED'
    """), {"box": payload.get("black_box_id"), "container": payload.get("container_id")})
    _complete_job(job.id)


def _process_destocking(job):
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload)
    request_id = payload.get("request_id")
    request_row = db.session.execute(text("""
        SELECT * FROM destocking_requests WHERE id=:id AND status='APPROVED' FOR UPDATE
    """), {"id": request_id}).fetchone()
    if not request_row:
        _complete_job(job.id)
        return
    pdf = generate_container_report_pdf(request_row.container_id)
    report_uid = str(uuid.uuid4())
    stored = store_private_document(f"generated_reports/destocking_{request_row.container_id}_{report_uid}.pdf", pdf)
    db.session.execute(text("""
        INSERT INTO generated_reports(report_uid,category,title,container_id,black_box_id,storage_key,mime_type,size,checksum)
        VALUES(CAST(:uid AS uuid),'DESTOCKING',:title,:container,:box,:key,'application/pdf',:size,:checksum)
    """), {"uid": report_uid, "title": f"Rapport de destockage {request_row.container_id}",
             "container": request_row.container_id, "box": request_row.black_box_id,
             "key": stored["storage_key"], "size": stored["size"], "checksum": stored["checksum"]})
    db.session.execute(text("UPDATE boite_noir SET id_conteneurs=NULL,status='unassigned',updated_at=NOW() WHERE id_boite=:box"), {"box": request_row.black_box_id})
    db.session.execute(text("""
        UPDATE black_box_container_assignments SET detached_at=NOW(),reason='DESTOCKING',
            status='DETACHED',visibility_until=NOW()+INTERVAL '24 hours'
        WHERE black_box_id=:box AND container_id=:container AND status='ACTIVE'
    """), {"box": request_row.black_box_id, "container": request_row.container_id})
    db.session.execute(text("""
        UPDATE destocking_requests SET status='COMPLETED',final_report_id=(SELECT id FROM generated_reports WHERE report_uid=CAST(:uid AS uuid)),updated_at=NOW()
        WHERE id=:id
    """), {"uid": report_uid, "id": request_id})
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,id_boite)
        VALUES('DESTOCKING_COMPLETED',:message,'all',:box)
    """), {"message": f"Destockage termine pour {request_row.container_id}. Rapport {report_uid} disponible.", "box": request_row.black_box_id})
    _complete_job(job.id)


def run_once(app):
    with app.app_context():
        jobs = db.session.execute(text("""
            SELECT * FROM background_jobs WHERE status='PENDING' AND run_at<=NOW()
            ORDER BY run_at LIMIT 20 FOR UPDATE SKIP LOCKED
        """)).fetchall()
        for job in jobs:
            try:
                db.session.execute(text("UPDATE background_jobs SET status='RUNNING',attempts=attempts+1,updated_at=NOW() WHERE id=:id"), {"id": job.id})
                if job.job_type == "REVOKE_DETACHED_CONTAINER_ACCESS":
                    _process_revoke(job)
                elif job.job_type == "DETACH_AFTER_DESTOCKING":
                    _process_destocking(job)
                else:
                    db.session.execute(text("UPDATE background_jobs SET status='FAILED',last_error='Type de tache inconnu',updated_at=NOW() WHERE id=:id"), {"id": job.id})
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                db.session.execute(text("""
                    UPDATE background_jobs SET status=CASE WHEN attempts>=5 THEN 'FAILED' ELSE 'PENDING' END,
                        last_error=:error,run_at=NOW()+INTERVAL '5 minutes',updated_at=NOW() WHERE id=:id
                """), {"error": str(exc)[:1000], "id": job.id})
                db.session.commit()
        archive_hours = int(app.config.get("NOTIFICATION_ARCHIVE_AFTER_HOURS", 168))
        db.session.execute(text("""
            UPDATE notifications SET status='archived'
            WHERE status='read' AND horodatage < NOW() - (:hours * INTERVAL '1 hour')
        """), {"hours": archive_hours})
        db.session.commit()
        return len(jobs)


def main():
    from app.migrate import run_migrations
    run_migrations()
    app = create_app()
    once = os.getenv("WORKER_ONCE", "0") == "1"
    while True:
        run_once(app)
        if once:
            return
        time.sleep(int(os.getenv("WORKER_POLL_SECONDS", "30")))


if __name__ == "__main__":
    main()
