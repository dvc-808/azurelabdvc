from __future__ import annotations

import urllib.parse
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .azure_clients import get_secret_value
from .settings import settings


_engine: Optional[Engine] = None


def _build_sqlalchemy_engine_from_odbc_conn_str(odbc_conn_str: str) -> Engine:
    # SQLAlchemy's pyodbc URI format requires urlencoded ODBC connection string
    encoded = urllib.parse.quote_plus(odbc_conn_str)
    uri = f"mssql+pyodbc:///?odbc_connect={encoded}"
    # Pooling tuned for App Service
    return create_engine(
        uri,
        pool_pre_ping=True,
        pool_recycle=180,
        pool_size=5,
        max_overflow=5,
        fast_executemany=True,
    )


def init_engine() -> Engine:
    global _engine
    if _engine is None:
        secret_name = settings.sql_connection_secret_name
        if not secret_name:
            raise RuntimeError("SQL connection secret name not configured")
        odbc_conn_str = get_secret_value(secret_name)
        if not odbc_conn_str:
            raise RuntimeError(f"Secret '{secret_name}' is empty or not found")
        _engine = _build_sqlalchemy_engine_from_odbc_conn_str(odbc_conn_str)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        return init_engine()
    return _engine


def fetch_user_profile(user_id: str) -> Optional[dict]:
    engine = get_engine()
    query = text(
        """
        SELECT TOP 1
            user_id,
            name,
            age,
            phone,
            address,
            photo_blob_name
        FROM dbo.Users
        WHERE user_id = :user_id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"user_id": user_id}).mappings().first()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "age": int(row["age"]) if row["age"] is not None else None,
            "phone": row["phone"],
            "address": row["address"],
            "photo_blob_name": row["photo_blob_name"],
        } 