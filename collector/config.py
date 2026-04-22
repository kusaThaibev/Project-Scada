import os
from dotenv import load_dotenv

# Load .env from the root directory
load_dotenv(dotenv_path="../.env")

# --- OPC UA Configuration ---
OPC_SERVER_URL = os.getenv("OPC_SERVER_URL", "opc.tcp://127.0.0.1:49320")
POLLING_INTERVAL = float(os.getenv("POLLING_INTERVAL", 1.0))
OPC_USER = os.getenv("OPC_USER", "")
OPC_PASSWORD = os.getenv("OPC_PASSWORD", "")

# --- Database Configuration ---
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# SQLite
DB_SQLITE_PATH = os.getenv("DB_SQLITE_PATH", "../database/scada_data.db")

# PostgreSQL
DB_POSTGRES = {
    "dbname": os.getenv("DB_NAME", "scada_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432))
}

# --- Performance Configuration ---
BATCH_SIZE = 100
