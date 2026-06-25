import sqlite3
import random
import time
import threading
from datetime import datetime
import db

DB_PATH = "machine_data.db"

def init_local_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS machine_status (
            id INTEGER PRIMARY KEY, machine_id TEXT, state TEXT, current_duration INTEGER,
            last_state TEXT, last_duration INTEGER, total_run INTEGER, total_idle INTEGER,
            total_breakdown INTEGER, updated_at DATETIME
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS machine_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT, state TEXT,
            start_time DATETIME, end_time DATETIME, duration_seconds INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT, timestamp DATETIME
        )
    """)

    c.execute("""
        INSERT OR IGNORE INTO machine_status 
        (id, machine_id, state, current_duration, last_state, last_duration, total_run, total_idle, total_breakdown, updated_at)
        VALUES (1, 'PRESS-07', 'running', 0, 'idle', 0, 0, 0, 0, datetime('now'))
    """)
    
    sensors = db.get_sensor_configs()
    comps = db.get_component_configs()
    for s in sensors:
        try: c.execute(f"ALTER TABLE machine_status ADD COLUMN {s['db_column']} REAL DEFAULT 0.0")
        except: pass
        try: c.execute(f"ALTER TABLE sensor_logs ADD COLUMN {s['db_column']} REAL DEFAULT 0.0")
        except: pass
    for comp in comps:
        try: c.execute(f"ALTER TABLE machine_status ADD COLUMN {comp['db_column']} INTEGER DEFAULT 1")
        except: pass

    conn.commit()
    conn.close()

def simulate(stop_event):
    state = "running"
    current_duration = 0
    last_state = "idle"
    last_duration = 0
    total_run = total_idle = total_breakdown = 0
    state_start_time = datetime.now()

    print("Dynamic Simulator running — Ctrl+C to stop.")

    while not stop_event.is_set():
        sensors = db.get_sensor_configs()
        comps = db.get_component_configs()
        
        new_state = state
        roll = random.random()
        
        if state == "running":
            if roll < 0.02: new_state = "idle"
            elif roll < 0.005: new_state = "breakdown"
        elif state == "idle":
            if roll < 0.1: new_state = "running"
        elif state == "breakdown":
            if roll < 0.01: new_state = "running"

        now = datetime.now()

        if new_state != state:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO machine_logs (machine_id, state, start_time, end_time, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            """, ('PRESS-07', state, state_start_time.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"), current_duration))
            conn.commit()
            conn.close()

            last_state = state
            last_duration = current_duration
            state = new_state
            current_duration = 0
            state_start_time = now

        current_duration += 1
        if state == "running": total_run += 1
        elif state == "idle": total_idle += 1
        elif state == "breakdown": total_breakdown += 1

        sensor_data = {}
        for s in sensors:
            val = round(random.uniform(s['sim_min'], s['sim_max']), 2) if state == "running" else 0.0
            sensor_data[s['db_column']] = val
            
        comp_data = {}
        for c in comps:
            is_ok = 0 if state == "breakdown" and random.random() < 0.05 else 1
            comp_data[c['db_column']] = is_ok

        conn = sqlite3.connect(DB_PATH)
        
        set_cols = ["state=?, current_duration=?, last_state=?, last_duration=?, total_run=?, total_idle=?, total_breakdown=?, updated_at=datetime('now')"]
        set_vals = [state, current_duration, last_state, last_duration, total_run, total_idle, total_breakdown]
        
        for k, v in {**sensor_data, **comp_data}.items():
            set_cols.append(f"{k}=?")
            set_vals.append(v)
            
        update_q = f"UPDATE machine_status SET {', '.join(set_cols)} WHERE machine_id='PRESS-07'"
        conn.execute(update_q, set_vals)

        if sensor_data:
            log_cols = ["machine_id", "timestamp"] + list(sensor_data.keys())
            log_vals = ["PRESS-07", now.strftime("%Y-%m-%d %H:%M:%S")] + list(sensor_data.values())
            placeholders = ", ".join(["?"] * len(log_vals))
            
            insert_q = f"INSERT INTO sensor_logs ({', '.join(log_cols)}) VALUES ({placeholders})"
            conn.execute(insert_q, log_vals)

        conn.commit()
        conn.close()
        time.sleep(1)

if __name__ == "__main__":
    init_local_db()
    stop_event = threading.Event()
    try: simulate(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
        print("\nSimulator stopped.")