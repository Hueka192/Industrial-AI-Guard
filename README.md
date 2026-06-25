# Industrial-AI-Guard

AI-powered industrial dashboard for real-time monitoring and diagnostics. Integrates with Siemens PLCs and uses local Ollama models with RAG to analyze live telemetry, historical CSVs, and PDF manuals completely offline.

## Features

- **Real-time Dashboard** — Monitor sensors, component health, and machine status (Running/Idle/Breakdown) with auto-refresh
- **Dual Data Source** — Local simulation mode for testing, or live connection to Siemens S7 PLCs via `snap7`
- **Historical Graphing** — Interactive matplotlib plots with polynomial trend fitting, date range selection, and hover annotations
- **AI Assistant (RAG)** — Chat with a local Ollama LLM (LLaMA 3) that has context from machine logs, sensor readings, and uploaded documents
- **Document Management** — View and manage PDF manuals, electrical/mechanical drawings, and other reference materials
- **Admin Panel** — Configure sensors/components, manage PLC connection settings, upload AI training documents, change passwords
- **Fully Offline** — No cloud dependencies; all AI inference runs locally via Ollama

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) (optional, for AI assistant) with `llama3` model pulled
- Siemens S7 PLC (optional, for live data)

### Install

```bash
git clone https://github.com/Hueka192/Industrial-AI-Guard.git
cd Industrial-AI-Guard
python -m venv venv
.\venv\Scripts\activate    # Windows
pip install PyQt6 matplotlib numpy ollama PyPDF2 snap7
```

### Run

```bash
python run_app.py
```

The dashboard opens with local simulation mode by default. The simulator generates realistic press machine data and sensor readings.

## Usage

| Action | How |
|--------|-----|
| View sensor history | Click any sensor card to open the live graph |
| Access documents | Click the **Documents** button in the toolbar |
| View machine logs | Click the **Time Log** button |
| Open admin panel | Click **Admin** — default password: `admin` |
| Ask the AI | Click **Ask AI** to open the RAG chat interface |
| Toggle fullscreen | Press **F11** |

### Admin Panel

From the admin panel you can:

- **Start/Stop** the local simulator
- **Add/Edit/Remove** sensors and components (name, unit, min/max range, alarm thresholds)
- **Switch** between local simulation and Siemens S7 PLC mode (configure IP, rack, slot)
- **Manage Documents** — upload PDFs, images, CSVs, and text files
- **Change** the admin password

### AI Assistant

The AI assistant (`Ask AI`) collects context from:

1. Uploaded AI documents (PDF, TXT, CSV, LOG)
2. Recent machine state transitions
3. Latest sensor readings

All processing stays local — no data leaves your network.

## Project Structure

```
Industrial-AI-Guard/
├── run_app.py              # Application entry point
├── main.py                 # Core dashboard GUI (MachineCard)
├── config.py               # Central configuration constants
├── db.py                   # Data access layer (SQLite + Siemens S7)
├── local_server.py         # Local machine simulator
├── admin.py                # Admin panel dialogs
├── LiveGraphing.py         # Historical sensor graphing (matplotlib)
├── ask_ai_ui.py            # AI assistant chat UI + RAG pipeline
├── timelog.py              # Machine state log viewer
├── assets/                 # Drawings, manuals, icons
├── .gitignore
└── README.md
```

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SIMULATION_PASSWORD` | `admin` | Admin panel password |
| `LOCAL_DB_PATH` | `machine_data.db` | SQLite database file |
| `MACHINE_ID` | `PRESS-07` | Machine identifier |
| `MACHINE_NAME` | `P65-CNC Machine` | Display name |
| `POLL_INTERVAL_MS` | `1000` | UI refresh interval (ms) |

Sensors and components are configured dynamically via the admin panel and stored in the database.

## Dependencies

| Library | Purpose |
|---------|---------|
| PyQt6 | GUI framework |
| matplotlib | Historical data plotting |
| numpy | Numerical operations, polynomial fitting |
| ollama | Local LLM inference (optional) |
| PyPDF2 | PDF text extraction (optional) |
| snap7 | Siemens S7 PLC communication (optional) |
| sqlite3 | Local data storage (stdlib) |


