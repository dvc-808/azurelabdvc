import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Key Vault
    key_vault_url: str = os.getenv("KEY_VAULT_URL", "")
    sql_connection_secret_name: str = os.getenv("SQL_CONNECTION_SECRET_NAME", "cuongdbstring")

    # Storage
    storage_account_url: str = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "")  # e.g. https://<account>.blob.core.windows.net
    storage_container_name: str = os.getenv("AZURE_BLOB_CONTAINER", "userphotos")

    # App
    environment: str = os.getenv("ENVIRONMENT", "production")


settings = Settings() 