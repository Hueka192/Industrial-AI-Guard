import sqlite3
import config
import datetime

try:
    import snap7
    from snap7.util import get_real, get_bool
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False

def _init_dynamic_tables():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                server_ip TEXT,
                use_local_db BOOLEAN,
                plc_rack INTEGER DEFAULT 0,
                plc_slot INTEGER DEFAULT 1
            )
        """)
        # Migration: add rack/slot columns for DBs created before this feature existed.
        # Must run before the INSERT below, since an old table lacks these columns.
        try: c.execute("ALTER TABLE app_settings ADD COLUMN plc_rack INTEGER DEFAULT 0")
        except: pass
        try: c.execute("ALTER TABLE app_settings ADD COLUMN plc_slot INTEGER DEFAULT 1")
        except: pass
        c.execute("INSERT OR IGNORE INTO app_settings (id, server_ip, use_local_db, plc_rack, plc_slot) VALUES (1, '', 1, 0, 1)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS sensor_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT, db_column TEXT, unit TEXT, sim_min REAL, sim_max REAL
            )
        """)
        if c.execute("SELECT COUNT(*) FROM sensor_config").fetchone()[0] == 0:
            default_sensors = [
                ("Voltage", "voltage", "V", 226.0, 236.0),
                ("Current", "current", "A", 14.0, 16.0),
                ("Temperature", "temperature", "°C", 65.0, 72.0),
                ("RPM", "rpm", "", 1430.0, 1470.0),
                ("Energy", "energy_consumption", "kW", 2.0, 4.0),
                ("Vibration", "vibration", "mm/s", 1.1, 1.6)
            ]
            c.executemany("INSERT INTO sensor_config (display_name, db_column, unit, sim_min, sim_max) VALUES (?, ?, ?, ?, ?)", default_sensors)

        c.execute("""
            CREATE TABLE IF NOT EXISTS component_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT, db_column TEXT
            )
        """)
        if c.execute("SELECT COUNT(*) FROM component_config").fetchone()[0] == 0:
            default_comps = [
                ("Main drive motor", "comp_main_drive"), ("Hydraulic pump", "comp_hydraulics"),
                ("Coolant pump", "comp_coolant"), ("Voltage regulator", "comp_voltage_reg"),
                ("Pressure relief valve", "comp_pressure"), ("Control board", "comp_control"),
                ("Temperature sensor", "comp_temp_sens"), ("Emergency stop relay", "comp_estop")
            ]
            c.executemany("INSERT INTO component_config (display_name, db_column) VALUES (?, ?)", default_comps)

        c.execute("""
            CREATE TABLE IF NOT EXISTS machine_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, path TEXT
            )
        """)
        if c.execute("SELECT COUNT(*) FROM machine_documents").fetchone()[0] == 0:
            defaults = [
                ("Electrical Drawing", config.ELECTRICAL_DRAWING),
                ("Mechanical Drawing", config.MECHANICAL_DRAWING),
                ("Machine Manual", config.MACHINE_MANUAL)
            ]
            c.executemany("INSERT INTO machine_documents (name, path) VALUES (?, ?)", defaults)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Init dynamic tables error: {e}")

_init_dynamic_tables()

# --- APP SETTINGS API ---
def get_app_settings():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
        conn.close()
        if row:
            d = dict(row)
            # Defensive defaults in case of an old row from before migration
            d.setdefault("plc_rack", 0)
            d.setdefault("plc_slot", 1)
            return d
        return {"server_ip": "", "use_local_db": True, "plc_rack": 0, "plc_slot": 1}
    except:
        return {"server_ip": "", "use_local_db": True, "plc_rack": 0, "plc_slot": 1}

def save_app_settings(server_ip, use_local_db, plc_rack=0, plc_slot=1):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("UPDATE app_settings SET server_ip=?, use_local_db=?, plc_rack=?, plc_slot=? WHERE id=1",
                     (server_ip, use_local_db, plc_rack, plc_slot))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# --- DYNAMIC CONFIG API ---
def get_sensor_configs():
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM sensor_config ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_component_configs():
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM component_config ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_sensor_config(name, db_col, unit, s_min, s_max):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        try: conn.execute(f"ALTER TABLE machine_status ADD COLUMN {db_col} REAL DEFAULT 0.0")
        except: pass
        try: conn.execute(f"ALTER TABLE sensor_logs ADD COLUMN {db_col} REAL DEFAULT 0.0")
        except: pass
        
        conn.execute("INSERT INTO sensor_config (display_name, db_column, unit, sim_min, sim_max) VALUES (?, ?, ?, ?, ?)", 
                     (name, db_col, unit, s_min, s_max))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def edit_sensor_config(old_db_col, new_name, new_db_col, new_unit):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        if old_db_col != new_db_col:
            try: conn.execute(f"ALTER TABLE machine_status ADD COLUMN {new_db_col} REAL DEFAULT 0.0")
            except: pass
            try: conn.execute(f"ALTER TABLE sensor_logs ADD COLUMN {new_db_col} REAL DEFAULT 0.0")
            except: pass
            
        conn.execute("UPDATE sensor_config SET display_name=?, db_column=?, unit=? WHERE db_column=?", 
                     (new_name, new_db_col, new_unit, old_db_col))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def delete_sensor_config(db_col):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM sensor_config WHERE db_column = ?", (db_col,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def add_component_config(name, db_col):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        try: conn.execute(f"ALTER TABLE machine_status ADD COLUMN {db_col} INTEGER DEFAULT 1")
        except: pass
        
        conn.execute("INSERT INTO component_config (display_name, db_column) VALUES (?, ?)", (name, db_col))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def edit_component_config(old_db_col, new_name, new_db_col):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        if old_db_col != new_db_col:
            try: conn.execute(f"ALTER TABLE machine_status ADD COLUMN {new_db_col} INTEGER DEFAULT 1")
            except: pass
            
        conn.execute("UPDATE component_config SET display_name=?, db_column=? WHERE db_column=?", 
                     (new_name, new_db_col, old_db_col))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def delete_component_config(db_col):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM component_config WHERE db_column = ?", (db_col,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

# --- LIVE DATA FETCH API (SIEMENS S7 PLCs) ---
def get_machine_data():
    settings = get_app_settings()
    if settings["use_local_db"] or not settings["server_ip"]:
        return _fetch_local()
    else:
        return _fetch_siemens_plc(settings["server_ip"], settings.get("plc_rack", 0), settings.get("plc_slot", 1))

def _fetch_local():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM machine_status WHERE machine_id = ?", (config.MACHINE_ID,)).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"DB error: {e}")
        return None

def _fetch_siemens_plc(server_ip, rack=0, slot=1):
    if not SNAP7_AVAILABLE:
        print("Error: python-snap7 is not installed.")
        return None
        
    try:
        plc = snap7.client.Client()
        plc.connect(server_ip, rack, slot)
        
        if not plc.get_connected():
            return None

        # rack/slot now come from app_settings (set in Customize Panels & PLC dialog).
        # Common values: S7-300/400 -> rack=0, slot=2 ; S7-1200/1500 -> rack=0, slot=1 (sometimes 0).
        # Change DB_NUMBER to match the actual Data Block inside TIA Portal
        DB_NUMBER = 1        
        READ_SIZE = 100      
        
        db_data = plc.db_read(DB_NUMBER, 0, READ_SIZE)
        
        data = {
            "state": "RUNNING", 
            "total_run": 0, "total_idle": 0, "total_breakdown": 0,
            "updated_at": str(datetime.datetime.now())
        }
        
        # 1. Parse Sensors (Floating Point / Real Numbers)
        sensors = get_sensor_configs()
        for s in sensors:
            offset_str = s["db_column"]
            try:
                byte_offset = int(offset_str)
                val = get_real(db_data, byte_offset)
                data[offset_str] = round(val, 2)
            except Exception as e:
                data[offset_str] = 0.0
                
        # 2. Parse Components (Booleans / Bits)
        comps = get_component_configs()
        for c in comps:
            offset_str = c["db_column"]
            try:
                byte_str, bit_str = str(offset_str).split('.')
                byte_offset = int(byte_str)
                bit_offset = int(bit_str)
                
                is_ok = get_bool(db_data, byte_offset, bit_offset)
                data[offset_str] = 1 if is_ok else 0
            except Exception as e:
                data[offset_str] = 1 
                
        plc.disconnect()
        return data

    except Exception as e:
        print(f"Snap7 connection/read error: {e}")
        return None

def get_sensor_history(sensor_col, start_time, end_time):
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        query = f"SELECT timestamp, {sensor_col} as val FROM sensor_logs WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC"
        rows = conn.execute(query, (start_str, end_str)).fetchall()
        conn.close()
        
        result = []
        for r in rows:
            try:
                dt = datetime.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
                result.append({"timestamp": dt, "val": r["val"]})
            except: pass
        return result
    except: return []

# --- DOCUMENTS / LOGS API ---
def get_documents():
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM machine_documents ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_document(name, path):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("INSERT INTO machine_documents (name, path) VALUES (?, ?)", (name, path))
        conn.commit()
        conn.close()
        return True
    except: return False

def rename_document(doc_id, new_name):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("UPDATE machine_documents SET name = ? WHERE id = ?", (new_name, doc_id))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_document(doc_id):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM machine_documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        return True
    except: return False

def get_logs():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM machine_logs ORDER BY id DESC LIMIT 100").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except: return []

def clear_logs():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM machine_logs")
        conn.commit()
        conn.close()
        return True
    except: return False

def clear_sensor_logs():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM sensor_logs")
        conn.commit()
        conn.close()
        return True
    except: return False

def format_runtime(seconds):
    if seconds < 60: return f"{seconds}s"
    hours = seconds // 3600
    mins  = (seconds % 3600) // 60
    secs  = seconds % 60
    if hours > 0: return f"{hours}h {mins}m {secs}s"
    return f"{mins}m {secs}s"

def get_ai_documents():
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM ai_documents ORDER BY name ASC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except: return []

def add_ai_document(name, path):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("INSERT INTO ai_documents (name, path) VALUES (?, ?)", (name, path))
        conn.commit()
        conn.close()
        return True
    except: return False

def rename_ai_document(doc_id, new_name):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("UPDATE ai_documents SET name = ? WHERE id = ?", (new_name, doc_id))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_ai_document(doc_id):
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        conn.execute("DELETE FROM ai_documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        return True
    except: return False