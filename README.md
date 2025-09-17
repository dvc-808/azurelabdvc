# FastAPI Azure Lab

A FastAPI app that reads SQL connection string from Azure Key Vault (secret name `cuongdbstring`), connects to a private Azure SQL Database using pyodbc, and serves user profiles including a photo from Azure Blob Storage. Designed to run on Azure App Service using Managed Identity.

## Features
- Uses Managed Identity for Key Vault and Storage
- SQLAlchemy + pyodbc to connect to Azure SQL (ODBC conn string from Key Vault)
- Jinja2 templates for simple UI
- Streams user photos from Blob Storage without exposing SAS

## Requirements
- Python 3.10+
- ODBC Driver 18 for SQL Server installed on the host
- Network access from App Service to private endpoints via VNet integration

## Environment Variables
- `KEY_VAULT_URL` (required): e.g. `https://<your-kv-name>.vault.azure.net`
- `SQL_CONNECTION_SECRET_NAME` (optional): defaults to `cuongdbstring`
- `AZURE_STORAGE_ACCOUNT_URL` (required): e.g. `https://<storage>.blob.core.windows.net`
- `AZURE_BLOB_CONTAINER` (optional): defaults to `userphotos`
- `ENVIRONMENT` (optional): `production` by default

## Database
Expected table `dbo.Users`:

```sql
CREATE TABLE dbo.Users (
  user_id NVARCHAR(128) NOT NULL PRIMARY KEY,
  name NVARCHAR(256) NOT NULL,
  age INT NULL,
  phone NVARCHAR(64) NULL,
  address NVARCHAR(512) NULL,
  photo_blob_name NVARCHAR(1024) NULL
);
```

The Key Vault secret `cuongdbstring` should contain a full ODBC connection string, e.g.:

```
Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<db>;
Authentication=ActiveDirectoryMsi;Encrypt=yes;TrustServerCertificate=no;
```

You may include `Application Intent=ReadOnly` if desired. If not using MSI for SQL, you can embed `Uid`/`Pwd` but MSI is recommended.

## Local Development
1. Install system deps (Ubuntu):
   - `sudo apt-get update && sudo apt-get install -y unixodbc unixodbc-dev msodbcsql18`
2. Create venv and install Python deps:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Set env vars for local run (if not using MSI locally):
   - `export KEY_VAULT_URL=...`
   - `export AZURE_STORAGE_ACCOUNT_URL=...`
   - `export AZURE_BLOB_CONTAINER=userphotos`
   - For local auth, DefaultAzureCredential can use `az login` or env creds.
4. Run:
   - `uvicorn app.main:app --reload`

## Azure App Service Deployment
- Assign a System-Assigned Managed Identity to the App Service
- Grant that identity access:
  - Key Vault: `get` on secrets
  - Storage Account: `Storage Blob Data Reader` role at account or container
  - Azure SQL: Create contained user from external provider and grant `db_datareader` (and needed perms)
- Configure App Settings:
  - `KEY_VAULT_URL`, `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_BLOB_CONTAINER`
- VNet integration to reach private endpoints (Key Vault, SQL, Storage)
- Startup command (optional): `gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app.main:app`

## Routes
- `GET /` Home page
- `GET /users/{user_id}` Profile page
- `GET /users/{user_id}/photo` Streams photo from Blob Storage
- `GET /healthz` Health check

## Notes
- The app initializes the DB on startup to fail fast if secrets or networking are misconfigured.
- Blob photo is proxied; no SAS token exposure. 