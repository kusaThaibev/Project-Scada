import asyncio
import logging
import sqlite3
from datetime import datetime
from asyncua import Client
import config

# Conditional import for PostgreSQL
try:
    import psycopg2
except ImportError:
    psycopg2 = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_type = config.DB_TYPE
        self.last_values = {} # Cache for deadband checking

    def get_connection(self):
        if self.db_type == "postgres":
            return psycopg2.connect(**config.DB_POSTGRES)
        else:
            return sqlite3.connect(config.DB_SQLITE_PATH)

    def get_active_tags(self):
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, opc_address, deadband FROM tag_config WHERE is_active = 1")
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    def update_snapshot_and_history(self, data_list):
        if not data_list:
            return
        
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 1. Update Snapshot (UPSERT)
            for tag_id, value, status, deadband in data_list:
                # Check deadband
                prev_val = self.last_values.get(tag_id)
                should_record = True
                
                try:
                    curr_float = float(value)
                    if prev_val is not None:
                        prev_float = float(prev_val)
                        if abs(curr_float - prev_float) < deadband:
                            should_record = False
                except:
                    # If not a number, record only if it changed as string
                    if str(value) == str(prev_val):
                        should_record = False

                # Always update snapshot
                snapshot_query = """
                INSERT INTO tag_latest_snapshot (tag_id, last_value, last_status, last_update)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tag_id) DO UPDATE SET
                    last_value=excluded.last_value,
                    last_status=excluded.last_status,
                    last_update=excluded.last_update
                """
                if self.db_type == "postgres":
                    snapshot_query = snapshot_query.replace("?", "%s").replace("ON CONFLICT(tag_id) DO UPDATE SET", "ON CONFLICT(tag_id) DO UPDATE SET")
                
                cur.execute(snapshot_query, (tag_id, str(value), status, now))
                
                # 2. Record to history if deadband passed
                if should_record:
                    history_query = "INSERT INTO raw_data_pool (tag_id, tag_value, status_code, timestamp) VALUES (?, ?, ?, ?)"
                    if self.db_type == "postgres":
                        history_query = history_query.replace("?", "%s")
                    cur.execute(history_query, (tag_id, str(value), status, now))
                    self.last_values[tag_id] = value

            conn.commit()
            logger.info(f"Updated {len(data_list)} tags.")
        except Exception as e:
            logger.error(f"Database Error: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()

async def monitor_tags():
    db = DatabaseManager()
    
    while True:
        try:
            logger.info(f"Connecting to OPC Server: {config.OPC_SERVER_URL}")
            client = Client(url=config.OPC_SERVER_URL)
            
            # Set credentials if provided
            if config.OPC_USER and config.OPC_PASSWORD:
                client.set_user(config.OPC_USER)
                client.set_password(config.OPC_PASSWORD)
            
            async with client:
                logger.info("Connected.")
                
                while True:
                    tags = db.get_active_tags()
                    if not tags:
                        await asyncio.sleep(5)
                        continue

                    data_to_process = []
                    for tag_id, address, deadband in tags:
                        try:
                            node = client.get_node(address)
                            val = await node.read_value()
                            data_to_process.append((tag_id, val, "Good", deadband))
                        except Exception as e:
                            logger.error(f"Read error {address}: {e}")
                            data_to_process.append((tag_id, None, "Error", deadband))

                    db.update_snapshot_and_history(data_to_process)
                    await asyncio.sleep(config.POLLING_INTERVAL)

        except Exception as e:
            logger.error(f"Connection lost: {e}. Retrying...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(monitor_tags())
