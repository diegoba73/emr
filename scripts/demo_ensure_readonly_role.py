#!/usr/bin/env python3
"""Idempotent: create demo read-only DB role + grants (SELECT + session/login exceptions).

Used by the demo stack after migrations. Connects as DB_ADMIN_* and configures
DB_USER / DB_PASSWORD as a LOGIN role that can:
  - SELECT on all tables/sequences in public
  - INSERT/UPDATE/DELETE on django_session (Django session auth)
  - UPDATE (last_login) only on the custom user table (usuarios; AUTH_USER_MODEL)

Does not grant broad INSERT/UPDATE/DELETE on clinical/business tables.
"""
from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2 import sql


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise SystemExit(f"demo_ensure_readonly_role: missing env {name}")
    return value


def main() -> int:
    host = _env("DB_HOST", "db")
    port = _env("DB_PORT", "5432")
    dbname = _env("DB_NAME", "synesis_db")
    admin_user = _env("DB_ADMIN_USER", "postgres")
    admin_password = _env("DB_ADMIN_PASSWORD")
    ro_user = _env("DB_USER")
    ro_password = _env("DB_PASSWORD")

    if ro_user == admin_user:
        print(
            "demo_ensure_readonly_role: DB_USER equals DB_ADMIN_USER; "
            "skipping (runtime is not read-only)."
        )
        return 0

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=admin_user,
        password=admin_password,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ro_user,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(
                        sql.Identifier(ro_user)
                    ),
                    (ro_password,),
                )
                print(f"Created role {ro_user}")
            else:
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(
                        sql.Identifier(ro_user)
                    ),
                    (ro_password,),
                )
                print(f"Updated password for role {ro_user}")

            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(dbname),
                    sql.Identifier(ro_user),
                )
            )
            cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(ro_user)
                )
            )
            cur.execute(
                sql.SQL(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}"
                ).format(sql.Identifier(ro_user))
            )
            cur.execute(
                sql.SQL(
                    "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(sql.Identifier(ro_user))
            )
            # Future tables created by the admin role (migrations).
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT ON TABLES TO {}"
                ).format(sql.Identifier(admin_user), sql.Identifier(ro_user))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT ON SEQUENCES TO {}"
                ).format(sql.Identifier(admin_user), sql.Identifier(ro_user))
            )

            # Login exceptions: sessions + last_login only.
            cur.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'django_session'
                """
            )
            if cur.fetchone():
                cur.execute(
                    sql.SQL(
                        "GRANT SELECT, INSERT, UPDATE, DELETE "
                        "ON TABLE django_session TO {}"
                    ).format(sql.Identifier(ro_user))
                )
            else:
                print("WARN: django_session missing; skip session grants", file=sys.stderr)

            # Custom AUTH_USER_MODEL (usuarios.User) uses db_table='usuarios'.
            # Fall back to auth_user if present (stock Django).
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('usuarios', 'auth_user')
                ORDER BY CASE table_name WHEN 'usuarios' THEN 0 ELSE 1 END
                LIMIT 1
                """
            )
            user_row = cur.fetchone()
            if user_row:
                user_table = user_row[0]
                # SELECT already covered by ALL TABLES; narrow write to last_login.
                cur.execute(
                    sql.SQL(
                        "GRANT UPDATE ({}) ON TABLE {} TO {}"
                    ).format(
                        sql.Identifier("last_login"),
                        sql.Identifier(user_table),
                        sql.Identifier(ro_user),
                    )
                )
                print(f"Granted UPDATE(last_login) on {user_table}")
            else:
                print(
                    "WARN: user table (usuarios/auth_user) missing; skip last_login grant",
                    file=sys.stderr,
                )

        print(f"Read-only grants applied for {ro_user}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
