from __future__ import annotations

from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, BlobClient

from .settings import settings


_credential: Optional[DefaultAzureCredential] = None
_secret_client: Optional[SecretClient] = None
_blob_service_client: Optional[BlobServiceClient] = None


def get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        # Managed Identity will be used automatically on App Service
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return _credential


def get_secret_client() -> SecretClient:
    global _secret_client
    if _secret_client is None:
        if not settings.key_vault_url:
            raise RuntimeError("KEY_VAULT_URL is not configured")
        _secret_client = SecretClient(vault_url=settings.key_vault_url, credential=get_credential())
    return _secret_client


def get_secret_value(secret_name: str) -> str:
    client = get_secret_client()
    secret = client.get_secret(secret_name)
    return secret.value


def get_blob_service_client() -> BlobServiceClient:
    global _blob_service_client
    if _blob_service_client is None:
        if not settings.storage_account_url:
            raise RuntimeError("AZURE_STORAGE_ACCOUNT_URL is not configured")
        _blob_service_client = BlobServiceClient(account_url=settings.storage_account_url, credential=get_credential())
    return _blob_service_client


def get_blob_client(blob_name: str) -> BlobClient:
    service = get_blob_service_client()
    return service.get_blob_client(container=settings.storage_container_name, blob=blob_name) 