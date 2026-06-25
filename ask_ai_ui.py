import os
import sqlite3
import config
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import PyPDF2
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

class OllamaWorker(QThread):
    text_chunk_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished_generation = pyqtSignal()

    def __init__(self, prompt, machine_context, documents):
        super().__init__()
        self.prompt = prompt
        self.machine_context = machine_context
        self.documents = documents

    def run(self):
        try:
            if not OLLAMA_AVAILABLE:
                self.error_occurred.emit("Ollama Python library is not installed. Run: pip install ollama")
                return

            context_text = ""
            
            # --- RAG: Read local PDFs, CSVs, and TXT files ---
            if self.documents:
                for doc in self.documents:
                    path = doc.get("path", "")
                    if os.path.exists(path):
                        ext = path.lower().split('.')[-1]
                        try:
                            if ext == 'pdf' and PYPDF_AVAILABLE:
                                with open(path, 'rb') as f:
                                    pdf_reader = PyPDF2.PdfReader(f)
                                    for page_num in range(min(3, len(pdf_reader.pages))):
                                        context_text += pdf_reader.pages[page_num].extract_text() + "\n"
                            elif ext in ['csv', 'txt', 'log']:
                                with open(path, 'r', encoding='utf-8') as f:
                                    context_text += f"\n--- Content of {os.path.basename(path)} ---\n"
                                    context_text += f.read()[:5000] + "\n"
                        except Exception as e:
                            print(f"Failed to read {path}: {e}")

            # --- RAG: Automatically pull Machine State changes ---
            db_history = "\n--- RECENT MACHINE STATE HISTORY ---\n"
            try:
                conn = sqlite3.connect(config.LOCAL_DB_PATH)
                conn.row_factory = sqlite3.Row
                logs = conn.execute("SELECT * FROM machine_logs ORDER BY id DESC LIMIT 5").fetchall()
                for log in reversed(logs):
                    db_history += f"[{log['start_time']}] State changed to {log['state'].upper()} (Duration: {log['duration_seconds']}s)\n"
            except Exception as e:
                db_history += "No state history available.\n"
                
            context_text += db_history

            # --- RAG: Pull LIVE SENSOR GRAPH TRENDS (Last 15 ticks) ---
            sensor_history = "\n--- RECENT SENSOR DATA TRENDS (Graph Data) ---\n"
            try:
                s_logs = conn.execute("SELECT * FROM sensor_logs ORDER BY id DESC LIMIT 15").fetchall()
                if s_logs:
                    for log in reversed(s_logs):
                        log_dict = dict(log)
                        ts = log_dict.pop('timestamp', 'Unknown Time')
                        log_dict.pop('id', None)
                        log_dict.pop('machine_id', None)
                        # Format the row into a readable string of sensor values
                        readings = ", ".join([f"{k}: {v}" for k, v in log_dict.items() if v is not None])
                        sensor_history += f"[{ts}] {readings}\n"
                else:
                    sensor_history += "No recent sensor data.\n"
                conn.close()
            except Exception as e:
                sensor_history += "Sensor history unavailable.\n"

            context_text += sensor_history

            # --- Final Prompt Assembly ---
            model_name = 'llama3' 
            system_prompt = (
                f"You are an expert industrial diagnostic AI. \n"
                f"CURRENT LIVE STATUS: State={self.machine_context.get('state', 'UNKNOWN')}\n"
            )
            
            for k, v in self.machine_context.items():
                if k not in ["state", "total_run", "total_idle", "total_breakdown", "updated_at", "machine_id", "id", "current_duration", "last_duration", "last_state"]:
                    system_prompt += f"{k}={v}  "
            
            if context_text:
                system_prompt += f"\n\nDOCUMENTATION & DATA LOGS:\n{context_text}\n\n"

            full_prompt = f"{system_prompt}\nUser Query: {self.prompt}"

            try:
                response = ollama.generate(model=model_name, prompt=full_prompt, stream=True)
                for chunk in response:
                    text = chunk.get('response', '')
                    self.text_chunk_received.emit(text)
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg:
                    self.error_occurred.emit(f"Model '{model_name}' not found. Please open your terminal and run:\nollama pull {model_name}")
                else:
                    self.error_occurred.emit(f"Failed to connect to local Ollama instance: {err_msg}")
                    
        finally:
            self.finished_generation.emit()

class AskAIDialog(QDialog):
    def __init__(self, machine_data, documents, parent=None):
        super().__init__(parent)
        self.machine_data = machine_data
        self.documents = documents
        self.setWindowTitle("AI Assistant - Predict & Diagnose")
        self.setMinimumSize(700, 600)
        
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlags(Qt.WindowType.Window)

        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        layout = QVBoxLayout(self)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # Forced color: black to fix visibility
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: white; color: black; border: 1px solid #cbd5e1; 
                border-radius: 8px; padding: 10px; font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about anomalies, trends, or current machine state...")
        # Forced color: black to fix visibility
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; 
                font-size: 14px; background: white; color: black;
            }
        """)
        self.input_field.returnPressed.connect(self.send_query)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton { background: #8b5cf6; color: white; padding: 12px 24px; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: #7c3aed; }
            QPushButton:disabled { background: #cbd5e1; }
        """)
        self.send_btn.clicked.connect(self.send_query)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.append_message("System", f"Ready. Connected to local AI. (Live Machine Status: {self.machine_data.get('state', 'UNKNOWN')})")

    def append_message(self, sender, text):
        color = "#8b5cf6" if sender == "AI" else "#475569" if sender == "System" else "#1d4ed8"
        self.chat_display.append(f'<span style="color:{color}"><b>{sender}:</b></span> {text}')

    def send_query(self):
        user_text = self.input_field.text().strip()
        if not user_text: return

        self.append_message("You", user_text)
        self.input_field.clear()
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        self.chat_display.append('<span style="color:#8b5cf6"><b>AI:</b></span> ')

        self.worker = OllamaWorker(user_text, self.machine_data, self.documents)
        self.worker.text_chunk_received.connect(self.handle_chunk)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.finished_generation.connect(self.reset_input)
        self.worker.start()

    def handle_chunk(self, chunk):
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_display.insertPlainText(chunk)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def handle_error(self, error_text):
        self.chat_display.append(f'<span style="color:red"><b>Error:</b> {error_text}</span>')

    def reset_input(self):
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()