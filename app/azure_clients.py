import os
import base64
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import (
	BlobServiceClient,
	BlobSasPermissions,
	generate_blob_sas,
)


def _get_required_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value


@lru_cache(maxsize=1)
def get_default_credential() -> DefaultAzureCredential:
	# Managed Identity on App Service will be used in production automatically
	return DefaultAzureCredential(exclude_shared_token_cache_credential=True)


@lru_cache(maxsize=1)
def get_key_vault_client() -> SecretClient:
	vault_url = _get_required_env("KEY_VAULT_URL")
	cred = get_default_credential()
	return SecretClient(vault_url=vault_url, credential=cred)


def get_secret_value(secret_name: str, secret_version: Optional[str] = None) -> str:
	client = get_key_vault_client()
	if secret_version:
		secret = client.get_secret(secret_name, secret_version)
	else:
		secret = client.get_secret(secret_name)
	return secret.value


@lru_cache(maxsize=1)
def get_blob_service_client() -> BlobServiceClient:
	account_url = _get_required_env("STORAGE_ACCOUNT_URL")
	cred = get_default_credential()
	return BlobServiceClient(account_url=account_url, credential=cred)


def generate_temporary_blob_sas_url(container_name: str, blob_name: str, expiry_minutes: int = 10) -> str:
	"""
	Generate a short-lived user-delegation SAS URL using Managed Identity.
	Works without storage account keys.
	"""
	service = get_blob_service_client()
	account_name = service.account_name
	now = datetime.now(timezone.utc)
	udk = service.get_user_delegation_key(key_start_time=now - timedelta(minutes=1), key_expiry_time=now + timedelta(minutes=expiry_minutes))
	sas = generate_blob_sas(
		account_name=account_name,
		container_name=container_name,
		blob_name=blob_name,
		user_delegation_key=udk,
		permission=BlobSasPermissions(read=True),
		expiry=now + timedelta(minutes=expiry_minutes),
	)
	return f"{service.url}/{container_name}/{blob_name}?{sas}"


def list_user_picture_blob_names(container_name: str, user_id: str) -> list[str]:
	"""
	List blobs for a given user. Convention: blobs are stored under prefix "{user_id}/".
	"""
	service = get_blob_service_client()
	container = service.get_container_client(container_name)
	prefix = f"{user_id}/"
	names: list[str] = []
	for item in container.list_blobs(name_starts_with=prefix):
		# skip "directories" markers
		if getattr(item, "name", None):
			names.append(item.name)
	return names 