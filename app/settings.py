import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Key Vault
    key_vault_url: str = "https://cuong-keyvault.vault.azure.net/"
    sql_connection_secret_name: str = "cuongdbstring"

    # Storage
    storage_account_url: str = "https://dvcdangcapvippro.blob.core.windows.net"
    storage_container_name: str = "profile-image"



settings = Settings() 