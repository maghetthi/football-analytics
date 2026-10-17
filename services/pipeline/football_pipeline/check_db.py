"""CLI: python -m football_pipeline.check_db

Connects with the configured settings and reports what is on the other end, without printing any
credential. Use it to validate a remote database before migrating (make neon-check).
"""

from sqlalchemy import Engine, create_engine, text

from football_pipeline.config import get_settings


def describe(engine: Engine) -> dict[str, object]:
    with engine.connect() as conn:
        version = conn.execute(text("select version()")).scalar_one()
        user = conn.execute(text("select current_user")).scalar_one()
        # Ask the client library, not the server: behind a proxy (Neon) pg_stat_ssl can say
        # "false" even though our own connection is encrypted.
        ssl = conn.connection.dbapi_connection.pgconn.ssl_in_use
        vector = conn.execute(
            text("select default_version from pg_available_extensions where name = 'vector'")
        ).scalar()
        can_create_role = conn.execute(
            text("select rolcreaterole or rolsuper from pg_roles where rolname = current_user")
        ).scalar()
    return {
        "server": version.split(",")[0],
        "connected_as": user,
        "tls": bool(ssl),
        "pgvector_available": vector,
        "can_create_roles": bool(can_create_role),
    }


def main() -> None:
    settings = get_settings()
    print(f"target: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    for key, value in describe(create_engine(settings.database_url)).items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
