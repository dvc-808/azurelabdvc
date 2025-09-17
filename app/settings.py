import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Key Vault (hardcoded)
    key_vault_url: str = "https://your-keyvault-name.vault.azure.net"
    sql_connection_secret_name: str = "cuongdbstring"

    # Storage (hardcoded)
    storage_account_url: str = "https://yourstorageaccount.blob.core.windows.net"
    storage_container_name: str = "profile-image"



settings = Settings() 