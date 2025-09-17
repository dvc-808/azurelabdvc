import os
import re
from contextlib import contextmanager
from typing import Iterator, Optional

import pyodbc
from azure.identity import DefaultAzureCredential

from .azure_clients import get_default_credential, get_secret_value


# Constant for pyodbc access token attribute
# Ref: https://learn.microsoft.com/sql/connect/odbc/using-azure-active-directory#access-token
SQL_COPT_SS_ACCESS_TOKEN = 1256


def _get_sql_secret_name() -> str:
	return os.getenv("SQL_KEY_SECRET_NAME", "cuongdbstring")


def _get_odbc_connection_string() -> str:
	secret_name = _get_sql_secret_name()
	conn_str = get_secret_value(secret_name)
	if not conn_str:
		raise RuntimeError(f"Key Vault secret '{secret_name}' is empty")
	return conn_str


def _contains_uid_pwd(conn_str: str) -> bool:
	return ("Uid=" in conn_str or "UID=" in conn_str or "User ID=" in conn_str) and (
		"Pwd=" in conn_str or "PWD=" in conn_str or "Password=" in conn_str
	)


def _extract_server_and_database(conn_str: str) -> tuple[Optional[str], Optional[str]]:
	server_match = re.search(r"Server\s*=\s*([^;]+)", conn_str, re.IGNORECASE)
	db_match = re.search(r"Database\s*=\s*([^;]+)", conn_str, re.IGNORECASE)
	server = server_match.group(1) if server_match else None
	database = db_match.group(1) if db_match else None
	return server, database


def _ensure_encrypt_options(conn_str: str) -> str:
	# Ensure secure defaults if not present
	parts = conn_str.strip().rstrip(";").split(";")
	kv = {}
	for p in parts:
		if not p:
			continue
		if "=" in p:
			k, v = p.split("=", 1)
			kv[k.strip()] = v.strip()
	# Set defaults if missing
	kv.setdefault("Encrypt", "yes")
	kv.setdefault("TrustServerCertificate", "no")
	kv.setdefault("Connection Timeout", "30")
	return ";".join([f"{k}={v}" for k, v in kv.items()]) + ";"


def _get_access_token_for_sql(credential: DefaultAzureCredential) -> bytes:
	token = credential.get_token("https://database.windows.net/.default")
	# pyodbc expects a bytes token with null terminator
	return bytes(token.token, "utf-8") + b"\0"


@contextmanager
def get_db_connection() -> Iterator[pyodbc.Connection]:
	"""
	Context manager that yields a live pyodbc connection.
	- If the secret contains username/password, uses it directly.
	- Otherwise, uses Managed Identity to fetch an AAD access token for Azure SQL.
	"""
	conn_str = _ensure_encrypt_options(_get_odbc_connection_string())
	connection: Optional[pyodbc.Connection] = None
	try:
		if _contains_uid_pwd(conn_str):
			connection = pyodbc.connect(conn_str)
		else:
			# Use AAD token with Managed Identity
			credential = get_default_credential()
			token = _get_access_token_for_sql(credential)
			connection = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token})
		yield connection
	finally:
		if connection is not None:
			connection.close()


def fetch_user_profile_by_id(user_id: str) -> Optional[dict]:
	"""
	Fetch a user profile by user_id. Expects a table named [Users]
	with columns: user_id (PK), name, age, phone, address.
	"""
	query = (
		"SELECT TOP 1 user_id, name, age, phone, address "
		"FROM dbo.Users WHERE user_id = ?"
	)
	with get_db_connection() as conn:
		cursor = conn.cursor()
		row = cursor.execute(query, user_id).fetchone()
		if not row:
			return None
		columns = [col[0] for col in cursor.description]
		return {columns[i]: row[i] for i in range(len(columns))} 