import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Key Vault
    key_vault_url: str = "kv.privatelink.vaultcore.azure.net"
    sql_connection_secret_name: str = "cuongdbstring"

    # Storage
    storage_account_url: str = "sa.privatelink.blob.core.windows.net"
    storage_container_name: str = "profile-image"



settings = Settings() 