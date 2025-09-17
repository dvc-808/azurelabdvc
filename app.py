from flask import Flask
import mysql.connector
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import base64
from azure.keyvault.secrets import SecretClient
 
 
app = Flask(__name__)
 
 
KEY_VAULT_URL = "https://cuong-keyvault.vault.azure.net/"
MYSQL_SECRET_NAME = "mysql-password"
 
 
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
 
# Config kết nối trực tiếp tới Azure MySQL
host = "mssqlsrvdvcdangcapvippro.mysql.database.azure.com"
database = "sqldb01"
user = "dvcdvc"
mysql_password = secret_client.get_secret(MYSQL_SECRET_NAME).value
 
 
# # Config Azure Blob


STORAGE_ACCOUNT_NAME = "dvcdangcapvippro"
STORAGE_CONTAINER_NAME = "profile-image"
BLOB_NAME = "avatar.png"
SA_CON = "saconstring"
sacon = secret_client.get_secret(SA_CON).value


blob_service_client = BlobServiceClient.from_connection_string(sacon)
 
@app.route("/test-secret")
def test_secret():
    return f"""
    MYSQL_PASSWORD loaded successfully: {mysql_password} <br>
    https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{STORAGE_CONTAINER_NAME}/{BLOB_NAME}
    """
@app.route("/health-check")
def test_secret():
    return "200"
@app.route("/")
def index():
    # Kết nối MySQL
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=mysql_password,
        database=database,
        port=3306,
        ssl_disabled=False,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT name, age, phone_number, address FROM person WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
 
 
    blob_client = blob_service_client.get_blob_client(container=STORAGE_CONTAINER_NAME, blob=BLOB_NAME)
    blob_data = blob_client.download_blob().readall()
 
    img_base64 = base64.b64encode(blob_data).decode("utf-8")
    img_tag = f'<img src="data:image/png;base64,{img_base64}" alt="User Avatar" width="200">'
 
 
    return f"""
    <h1>User Info</h1>
    <p>Name: {row[0]}</p>
    <p>Age: {row[1]}</p>
    <p>Phone: {row[2]}</p>
    <p>Address: {row[3]}</p>
    <h2>Pictures</h2>
    {img_tag}
    """
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)