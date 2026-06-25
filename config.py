import sys
import os

def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# ── Security ─────────────────────────────────────────────
SIMULATION_PASSWORD = "admin"

# ── Local DB (development) ───────────────────────────────
LOCAL_DB_PATH = "machine_data.db"

# ── Machine ──────────────────────────────────────────────
MACHINE_ID   = "PRESS-07"
MACHINE_NAME = "P65-CNC Machine"

# ── Poll interval ─────────────────────────────────────────
POLL_INTERVAL_MS = 1000

# ── Documents ─────────────────────────────────────────────
ELECTRICAL_DRAWING = get_resource_path("assets/electrical.jpg")
MECHANICAL_DRAWING = get_resource_path("assets/mechanical.jpg")
MACHINE_MANUAL     = get_resource_path("assets/manual.pdf")