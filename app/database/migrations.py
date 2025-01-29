import logging

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError


def migrate(engine: Engine):
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF;"))  # optional: reduce constraints while migrating

        # 1) Ensure the 'schema_version' table exists
        create_version_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1), 
                version INTEGER NOT NULL
            );
        """
        conn.execute(text(create_version_table_sql))

        # 2) If no row in schema_version, initialize version to 0
        init_version_sql = """
            INSERT OR IGNORE INTO schema_version (id, version)
            VALUES (1, 0);
        """
        conn.execute(text(init_version_sql))
        conn.commit()

        # 3) Get the current version
        current_version_sql = "SELECT version FROM schema_version WHERE id = 1;"
        current_version = conn.execute(text(current_version_sql)).scalar()

        # 4) Apply migrations step-by-step until we’re at the latest version
        #    Each migration block is guarded by an if-check on current_version.

        # -- MIGRATION 1: From version 0 -> 1
        if current_version < 1:
            try:
                conn.execute(text("""
                    ALTER TABLE top5_pipelines ADD COLUMN logs TEXT;
                """))
            except OperationalError as e:
                print(f"Error applying migration 1: {e}")

            # Update version to 1
            conn.execute(text("UPDATE schema_version SET version = 1 WHERE id = 1;"))
            conn.commit()
            current_version = 1

        conn.execute(text("PRAGMA foreign_keys=ON;"))
        conn.commit()

    logging.info(f"Migrations completed. Current version: {current_version}")
