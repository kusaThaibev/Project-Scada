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

    for filename in csv_files:
        filepath = os.path.join(TAG_FOLDER, filename)
        print(f"\nProcessing {filename}...")
        
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Updated required fields to use machine_name
            required_fields = ['machine_name', 'tag_name', 'opc_address', 'deadband', 'description']
            if not all(field in reader.fieldnames for field in reader.fieldnames if field in required_fields):
                # Check specifically for machine_name
                if 'machine_name' not in reader.fieldnames:
                    print(f"Skip {filename}: Missing 'machine_name' column")
                    continue

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

                    # 2. Insert or Update Tag Config
                    sql = """
                    INSERT INTO tag_config (machine_id, tag_name, opc_address, deadband, description, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(opc_address) DO UPDATE SET
                        machine_id=excluded.machine_id,
                        tag_name=excluded.tag_name,
                        deadband=excluded.deadband,
                        description=excluded.description
                    """
                    
                    params = (
                        machine_id, 
                        row['tag_name'].strip(), 
                        row['opc_address'].strip(), 
                        float(row['deadband']), 
                        row['description'].strip()
                    )
                    
                    if config.DB_TYPE == "postgres":
                        sql = sql.replace("?", "%s")
                    
                    cur.execute(sql, params)
                    print(f"  - Imported Tag: {row['tag_name']}")
                    
                except Exception as e:
                    print(f"  - Error importing row {row.get('tag_name')}: {e}")

    conn.commit()
    conn.close()
    print("\n✅ All CSV files processed successfully.")

if __name__ == "__main__":
    import_from_csv()
