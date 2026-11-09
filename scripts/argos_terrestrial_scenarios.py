#!/usr/bin/env python3
"""Worker for ARGOS's isolated, two-route terrestrial demo simulator.

Create and control sessions in the authenticated map UI. Keep this worker
running beside Flask; it resumes active sessions after a restart without
counting the period when the worker was offline.
"""

import argparse
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Traiter un cycle puis quitter (diagnostic)")
    parser.add_argument("--poll-seconds", type=float, default=2.0,
                        help="Période de vérification des sessions (défaut : 2 s)")
    args = parser.parse_args()
    if args.poll_seconds < 0.5 or args.poll_seconds > 30:
        parser.error("--poll-seconds doit être compris entre 0,5 et 30")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from app.migrate import run_migrations
    run_migrations()
    from app import create_app
    from app.extensions import db
    from app.services.terrestrial_simulation_service import process_one_simulation_tick
    from sqlalchemy import text

    app = create_app()
    stop = {"requested": False}

    def request_stop(_signum, _frame):
        stop["requested"] = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    with app.app_context():
        # Session-level PostgreSQL lock prevents duplicate worker processes.
        lock_connection = db.engine.connect()
        acquired = lock_connection.execute(text(
            "SELECT pg_try_advisory_lock(hashtext('argos-terrestrial-simulation-worker'))"
        )).scalar()
        lock_connection.commit()
        if not acquired:
            lock_connection.close()
            raise SystemExit("Un worker de simulation ARGOS est déjà actif.")
        print("Worker ARGOS terrestre prêt; les sessions restent isolées des mesures et alertes opérationnelles.", flush=True)
        try:
            while True:
                rows = db.session.execute(text("""
                    SELECT session_uid FROM brady.argos_transport_sim_sessions
                    WHERE status='RUNNING' ORDER BY created_at
                """)).fetchall()
                for row in rows:
                    if stop["requested"]:
                        break
                    session_uid = str(row.session_uid)
                    try:
                        result = process_one_simulation_tick(session_uid)
                        if result.get("status") == "tick":
                            print(f"{session_uid} · {result['elapsed_seconds']:.0f}s · {result['scenarios']}", flush=True)
                    except Exception as exc:
                        db.session.rollback()
                        app.logger.exception("Cycle de simulation interrompu temporairement pour %s", session_uid)
                        try:
                            db.session.execute(text("""
                                UPDATE brady.argos_transport_sim_sessions
                                SET last_error=:error,updated_at=NOW()
                                WHERE session_uid=CAST(:uid AS uuid) AND status='RUNNING'
                            """), {"uid": session_uid, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
                if args.once or stop["requested"]:
                    break
                time.sleep(args.poll_seconds)
        finally:
            db.session.remove()
            try:
                lock_connection.execute(text(
                    "SELECT pg_advisory_unlock(hashtext('argos-terrestrial-simulation-worker'))"
                ))
                lock_connection.commit()
            finally:
                lock_connection.close()
        print("Worker arrêté proprement; les sessions actives pourront reprendre au prochain démarrage.", flush=True)


if __name__ == "__main__":
    main()
