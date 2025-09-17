# FastAPI Azure Lab

A FastAPI app demonstrating secure connections to:
- Azure SQL (private)
- Azure Key Vault (secrets)
- Azure Blob Storage (pictures)

The app uses Managed Identity on Azure App Service to authenticate to Key Vault, Storage (user delegation SAS), and optionally to Azure SQL (AAD token) if the connection string does not include SQL username/password.

## Endpoints
- `GET /healthz` - health probe
- `GET /me` - returns the current user's profile and signed URLs to pictures in Blob Storage. The user identity is resolved from:
  1. `X-MS-CLIENT-PRINCIPAL-ID` (App Service EasyAuth)
  2. `X-User-Id` header
  3. `?user_id=` query param (local testing only)

## Data Model
Expected table `dbo.Users` with columns: `user_id` (PK), `name`, `age`, `phone`, `address`.

Pictures are stored in Blob Storage under prefix `user_id/` in container `${PHOTOS_CONTAINER}` (default `user-photos`).

## Configuration
Set these environment variables (App Settings in App Service or `.env` locally):

- `KEY_VAULT_URL` = `https://<kv-name>.vault.azure.net/`
- `STORAGE_ACCOUNT_URL` = `https://<storage>.blob.core.windows.net`
- `PHOTOS_CONTAINER` = `user-photos`
- `SQL_KEY_SECRET_NAME` = `cuongdbstring` (or override)

In Key Vault, create a secret named `cuongdbstring` with an ODBC connection string, e.g. one of:

- SQL Auth:
  `Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<db>;Uid=<user>;Pwd=<password>;Encrypt=yes;TrustServerCertificate=no;`
- AAD (Managed Identity):
  `Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<db>;Encrypt=yes;TrustServerCertificate=no;`

If using AAD, ensure the App Service Managed Identity has `Azure AD Admin` configured on the SQL Server and `db_datareader` permission on the database.

## Running Locally
1. Install system dependencies: ODBC Driver 18 for SQL Server and `unixodbc-dev`.
2. Create and fill `.env` using `.env.example`.
3. Install Python deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run:

```bash
uvicorn app.main:app --reload --port 8000
```

5. Test:

```bash
curl -H 'X-User-Id: alice' http://localhost:8000/me
```

## Azure Setup Notes
- Enable System Assigned Managed Identity on the App Service.
- Grant the identity access:
  - Key Vault: `get` on secrets.
  - Storage: `Storage Blob Data Reader` or `Storage Blob Data Contributor` as needed for user delegation SAS.
  - SQL: If using AAD, assign appropriate database roles. If using SQL Auth, no AAD role needed.
- For private endpoints, ensure DNS resolution for Key Vault, Storage, and SQL resolves to the private endpoints within your VNet and that App Service has VNet integration.

## Pictures
Upload user pictures to container `${PHOTOS_CONTAINER}` at path `user_id/<filename>`. The `/me` endpoint returns signed URLs valid for ~10 minutes. 