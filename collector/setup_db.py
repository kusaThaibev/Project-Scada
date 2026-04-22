import sqlite3
import os

DB_PATH = "../database/scada_data.db"
SCHEMA_PATH = "../database/schema.sql"

def setup():
    print(f"Initializing Machine-Based Database: {DB_PATH}")
    # Remove existing DB to apply new schema properly in test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
        
    conn.executescript(schema)
    
    cur = conn.cursor()
    
    # 1. Add Default Machines
    print("Adding default machines...")
    machines = [('Production Line 1', 'Main assembly line'), ('Utilities', 'Power and Water')]
    cur.executemany("INSERT INTO machines (machine_name, description) VALUES (?, ?)", machines)
    conn.commit()

    # 2. Add Sample Tags
    print("Adding sample tags...")
    sample_tags = [
        (1, 'Conveyor_Speed', 'ns=2;s=Line1.Conveyor.Speed', 1, 0.5, 'Speed in m/s'),
        (1, 'Motor_Current', 'ns=2;s=Line1.Motor.Amps', 1, 0.1, 'Current in Amperes'),
        (2, 'Total_Power', 'ns=2;s=Global.Energy.Total', 1, 1.0, 'Total power consumption')
    ]
    cur.executemany(
        "INSERT INTO tag_config (machine_id, tag_name, opc_address, is_active, deadband, description) VALUES (?, ?, ?, ?, ?, ?)",
        sample_tags
    )
    conn.commit()
    
    conn.close()
    print("\n✅ Setup Complete!")
    print("Next steps:")
    print("1. Put your CSV files in the 'Tag' folder.")
    print("2. Run 'python import_csv_tags.py' to import them.")
    print("3. Run 'python main.py' to start collecting data.")

if __name__ == "__main__":
    setup()
