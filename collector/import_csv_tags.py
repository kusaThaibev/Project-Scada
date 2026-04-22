import os
import csv
import sqlite3
import sys

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

TAG_FOLDER = "Tag"

def import_from_csv():
    if not os.path.exists(TAG_FOLDER):
        print(f"Error: Folder '{TAG_FOLDER}' not found.")
        return

    if config.DB_TYPE == "sqlite":
        conn = sqlite3.connect(config.DB_SQLITE_PATH)
    else:
        import psycopg2
        conn = psycopg2.connect(**config.DB_POSTGRES)
    
    cur = conn.cursor()
    
    csv_files = [f for f in os.listdir(TAG_FOLDER) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in {TAG_FOLDER}")
        return

    print(f"Found {len(csv_files)} files: {csv_files}")

    # --- DELETE/DEACTIVATE LOGIC ---
    # We will keep track of all OPC addresses found in ALL CSV files
    all_csv_addresses = []

    for filename in csv_files:
        filepath = os.path.join(TAG_FOLDER, filename)
        print(f"\nProcessing {filename}...")
        
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # 1. Get or Create Machine
                    machine_name = row['machine_name'].strip()
                    cur.execute("INSERT OR IGNORE INTO machines (machine_name) VALUES (?)", (machine_name,))
                    if config.DB_TYPE == "sqlite":
                        cur.execute("SELECT id FROM machines WHERE machine_name = ?", (machine_name,))
                    else:
                        cur.execute("SELECT id FROM machines WHERE machine_name = %s", (machine_name,))
                    machine_id = cur.fetchone()[0]

                    # 2. Insert or Update Tag Config (Set to Active)
                    address = row['opc_address'].strip()
                    all_csv_addresses.append(address)
                    
                    sql = """
                    INSERT INTO tag_config (machine_id, tag_name, opc_address, deadband, description, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(opc_address) DO UPDATE SET
                        machine_id=excluded.machine_id,
                        tag_name=excluded.tag_name,
                        deadband=excluded.deadband,
                        description=excluded.description,
                        is_active=1
                    """
                    
                    params = (
                        machine_id, 
                        row['tag_name'].strip(), 
                        address, 
                        float(row['deadband']), 
                        row['description'].strip()
                    )
                    
                    if config.DB_TYPE == "postgres":
                        sql = sql.replace("?", "%s")
                    
                    cur.execute(sql, params)
                    print(f"  - Imported/Updated Tag: {row['tag_name']}")
                    
                except Exception as e:
                    print(f"  - Error importing row: {e}")

    # --- DEACTIVATE TAGS NOT IN CSV ---
    # Any tag in the DB that is NOT in our all_csv_addresses list will be set to is_active = 0
    if all_csv_addresses:
        placeholders = ','.join(['?' for _ in all_csv_addresses])
        if config.DB_TYPE == "postgres":
            placeholders = ','.join(['%s' for _ in all_csv_addresses])
            
        deactivate_sql = f"UPDATE tag_config SET is_active = 0 WHERE opc_address NOT IN ({placeholders})"
        cur.execute(deactivate_sql, all_csv_addresses)
        
        deactivated_count = cur.rowcount
        print(f"\nℹ️ Deactivated {deactivated_count} tags that were NOT in the CSV files.")

    conn.commit()
    conn.close()
    print("\n✅ Sync with CSV files completed successfully.")

if __name__ == "__main__":
    import_from_csv()
