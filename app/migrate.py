"""Exécuteur de migrations SQL ARGOS, transactionnel et concurrent-safe."""

import hashlib
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "migrations"


def run_migrations():
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL obligatoire")
    connection = psycopg2.connect(database_url)
    connection.autocommit = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(hashtext('argos-schema-migrations'))")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS brady")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS brady.schema_migrations(
                    filename TEXT PRIMARY KEY, checksum_sha256 VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            connection.commit()
            for path in sorted(MIGRATIONS.glob("*.sql")):
                content = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                cursor.execute("SELECT checksum_sha256 FROM brady.schema_migrations WHERE filename=%s", (path.name,))
                existing = cursor.fetchone()
                if existing and existing[0] == checksum:
                    continue
                try:
                    cursor.execute(content)
                    cursor.execute("""
                        INSERT INTO brady.schema_migrations(filename,checksum_sha256,applied_at)
                        VALUES(%s,%s,NOW()) ON CONFLICT(filename) DO UPDATE SET
                        checksum_sha256=EXCLUDED.checksum_sha256,applied_at=NOW()
                    """, (path.name, checksum))
                    connection.commit()
                    print(f"Migration appliquee: {path.name}")
                except Exception:
                    connection.rollback()
                    raise
            cursor.execute("SELECT pg_advisory_unlock(hashtext('argos-schema-migrations'))")
            connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    run_migrations()
