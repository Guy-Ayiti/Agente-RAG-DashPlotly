"""
Configuración del checkpointer de LangGraph 1.0 sobre PostgreSQL (Supabase).

API basada en docs oficiales:
  docs.langchain.com/oss/python/langgraph/add-memory
  docs.langchain.com/oss/python/langgraph/persistence

Las 4 tablas que crea ``setup()`` (checkpoints, checkpoint_blobs,
checkpoint_writes, checkpoint_migrations) viven dentro del schema
indicado por ``DB_SCHEMA`` para mantenerlas aisladas del resto del
proyecto en Supabase.
"""

import os
from urllib.parse import quote_plus, urlencode

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver


def build_database_url() -> str:
    """
    Construye el connection string de Postgres a partir de las variables
    de entorno DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA.

    - La contraseña se URL-encodea con ``quote_plus`` para soportar
      caracteres especiales sin romper el parsing del URI.
    - ``sslmode=require`` es necesario para Supabase.
    - Si ``DB_SCHEMA`` no es ``public``, se embebe la opción libpq
      ``-c search_path=<schema>,public`` para que ``setup()`` cree sus
      tablas dentro de ese schema.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "postgres")
    schema = os.getenv("DB_SCHEMA", "public")

    missing = [k for k, v in {
        "DB_USER": user,
        "DB_PASSWORD": password,
        "DB_HOST": host,
    }.items() if not v]
    if missing:
        raise ValueError(
            "Faltan variables de entorno requeridas para el histórico: "
            + ", ".join(missing)
        )

    params = {"sslmode": "require"}
    if schema and schema != "public":
        params["options"] = f"-c search_path={schema},public"

    query = urlencode(params)
    return (
        f"postgresql://{user}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?{query}"
    )


def get_schema_name() -> str:
    """Schema de Postgres donde vivirán las tablas del checkpointer."""
    return os.getenv("DB_SCHEMA", "public")


# Estado interno: conexión y checkpointer vivos por todo el proceso.
_checkpointer: PostgresSaver | None = None
_TABLES_READY = False


def get_checkpointer() -> PostgresSaver:
    """Devuelve un ``PostgresSaver`` con conexión psycopg persistente.

    No se usa ``PostgresSaver.from_conn_string(...)`` (el patrón ``with``
    de las docs) porque al cachearlo en Streamlit la referencia al
    context manager se pierde y Python cierra la conexión por GC. En su
    lugar, abrimos la conexión directamente y la mantenemos viva como
    variable de módulo durante toda la vida del proceso.

    Flags importantes para Supabase:
    - ``autocommit=True``: las migrations y operaciones del saver son
      cada una en su propia transacción.
    - ``prepare_threshold=0``: desactiva *prepared statements*, que no
      son soportadas por el pooler de Supabase (pgbouncer / Supavisor
      en transaction mode).
    """
    global _checkpointer
    if _checkpointer is None:
        conn = psycopg.connect(
            build_database_url(),
            autocommit=True,
            prepare_threshold=0,
        )
        _checkpointer = PostgresSaver(conn)
    return _checkpointer


def ensure_checkpointer_tables() -> None:
    """
    Garantiza que el schema exista y que las tablas del checkpointer
    estén creadas. Idempotente y cacheado en memoria por proceso.

    Es seguro re-ejecutar: ``CREATE SCHEMA IF NOT EXISTS`` y
    ``checkpointer.setup()`` son idempotentes.
    """
    global _TABLES_READY
    if _TABLES_READY:
        return

    schema = get_schema_name()

    # 1. CREATE SCHEMA defensivo. Usamos una conexión efímera porque
    #    `search_path` no aplica al propio CREATE SCHEMA.
    if schema != "public":
        with psycopg.connect(build_database_url(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    # 2. Crear las 4 tablas del checkpointer dentro del schema activo.
    get_checkpointer().setup()

    _TABLES_READY = True
