from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QMessageBox, QLineEdit, QWidget, QTableWidget, QRadioButton,
    QTableWidgetItem, QHeaderView, QFileDialog, QInputDialog, QAbstractItemView, QTabWidget, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QColor
import config
import db
import os
import shutil

class CustomizationDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Customize Dashboard Panels & PLC Connection")
        self.setMinimumSize(700, 550)
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLabel { color: #1e293b; }
            QRadioButton { color: #1e293b; font-weight: 500; }
            QLineEdit { padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; color: black; background: white; }
            QTableWidget { background: white; color: black; border: 1px solid #cbd5e1; outline: none; }
            QTableWidget::item { color: black; padding: 4px; }
            QTableWidget::item:selected { background-color: #e0f2fe; color: black; }
            QHeaderView::section { background-color: #f1f5f9; color: black; padding: 6px; border: 1px solid #cbd5e1; font-weight: bold; }
            QPushButton { background: #3b82f6; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #2563eb; }
        """)

        layout = QVBoxLayout(self)
        conn_group = QWidget()
        conn_layout = QVBoxLayout(conn_group)
        self.local_radio = QRadioButton("Use Local Simulator Database")
        self.remote_radio = QRadioButton("Connect Directly to Siemens S7 PLC")
        self.remote_radio.toggled.connect(self._update_plc_fields_enabled)
        
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("PLC IP:"))
        self.ip_input = QLineEdit()
        ip_layout.addWidget(self.ip_input)
        
        rack_slot_layout = QHBoxLayout()
        rack_slot_layout.addWidget(QLabel("Rack:"))
        self.rack_input = QSpinBox()
        self.rack_input.setRange(0, 7)
        rack_slot_layout.addWidget(self.rack_input)
        rack_slot_layout.addWidget(QLabel("Slot:"))
        self.slot_input = QSpinBox()
        self.slot_input.setRange(0, 31)
        rack_slot_layout.addWidget(self.slot_input)
        
        conn_layout.addWidget(self.local_radio)
        conn_layout.addWidget(self.remote_radio)
        conn_layout.addLayout(ip_layout)
        conn_layout.addLayout(rack_slot_layout)
        layout.addWidget(conn_group)

        tabs = QTabWidget()
        layout.addWidget(tabs)
        sensor_tab = QWidget()
        s_layout = QVBoxLayout(sensor_tab)
        self.s_table = QTableWidget()
        self.s_table.setColumnCount(3)
        self.s_table.setHorizontalHeaderLabels(["Name", "PLC Offset", "Unit"])
        self.s_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.s_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        s_layout.addWidget(self.s_table)
        tabs.addTab(sensor_tab, "Live Readings")

        comp_tab = QWidget()
        c_layout = QVBoxLayout(comp_tab)
        self.c_table = QTableWidget()
        self.c_table.setColumnCount(2)
        self.c_table.setHorizontalHeaderLabels(["Name", "PLC Offset"])
        self.c_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.c_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        c_layout.addWidget(self.c_table)
        tabs.addTab(comp_tab, "Components")

        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_and_close)
        layout.addWidget(save_btn)
        self.load_data()

    def _update_plc_fields_enabled(self):
        is_remote = self.remote_radio.isChecked()
        self.ip_input.setEnabled(is_remote)
        self.rack_input.setEnabled(is_remote)
        self.slot_input.setEnabled(is_remote)

    def load_data(self):
        settings = db.get_app_settings()
        self.ip_input.setText(settings["server_ip"])
        self.rack_input.setValue(settings.get("plc_rack", 0))
        self.slot_input.setValue(settings.get("plc_slot", 1))
        if settings["use_local_db"]: self.local_radio.setChecked(True)
        else: self.remote_radio.setChecked(True)
        self._update_plc_fields_enabled()

    def save_and_close(self):
        db.save_app_settings(self.ip_input.text().strip(), self.local_radio.isChecked(), self.rack_input.value(), self.slot_input.value())
        self.accept()
        self.main_window.rebuild_ui()


class AdminDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Panel")
        self.setMinimumWidth(350)
        self.main_window = main_window
        self.setStyleSheet("AdminDialog { background-color: white; }")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Admin Controls")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.sim_btn = QPushButton()
        self._apply_standard_btn_style(self.sim_btn)
        self.update_sim_btn_text()
        self.sim_btn.clicked.connect(self.toggle_sim)
        layout.addWidget(self.sim_btn)

        self.custom_btn = QPushButton("⚙ Customize Panels & PLC Connection")
        self._apply_standard_btn_style(self.custom_btn)
        self.custom_btn.clicked.connect(self.open_customization)
        layout.addWidget(self.custom_btn)
        
        self.manage_docs_btn = QPushButton("Manage Standard Documents")
        self._apply_standard_btn_style(self.manage_docs_btn)
        self.manage_docs_btn.clicked.connect(self.manage_documents)
        layout.addWidget(self.manage_docs_btn)

        self.manage_ai_docs_btn = QPushButton("🧠 Manage AI Training Files")
        self._apply_standard_btn_style(self.manage_ai_docs_btn)
        self.manage_ai_docs_btn.clicked.connect(self.manage_ai_documents)
        layout.addWidget(self.manage_ai_docs_btn)

    def _apply_standard_btn_style(self, btn):
        btn.setStyleSheet("background: #e2e8f0; border-radius: 8px; padding: 15px; font-weight: bold; color: black;")

    def update_sim_btn_text(self):
        settings = db.get_app_settings()
        if not settings["use_local_db"]:
            self.sim_btn.setText("Mode: LIVE PLC DATA\n(Simulator Disabled)")
            self.sim_btn.setEnabled(False)
            return
        self.sim_btn.setEnabled(True)
        if self.main_window.is_simulating:
            self.sim_btn.setText("Simulation is ON\nClick to turn OFF")
        else:
            self.sim_btn.setText("Simulation is OFF\nClick to turn ON")

    def open_customization(self):
        dlg = CustomizationDialog(self.main_window, self)
        dlg.exec()
        self.update_sim_btn_text()

    def toggle_sim(self):
        self.main_window.toggle_simulation()
        self.update_sim_btn_text()

    def manage_documents(self):
        dlg = ManageDocumentsDialog(self, is_ai=False)
        dlg.exec()

    def manage_ai_documents(self):
        dlg = ManageDocumentsDialog(self, is_ai=True)
        dlg.exec()


class ManageDocumentsDialog(QDialog):
    def __init__(self, parent=None, is_ai=False):
        super().__init__(parent)
        self.is_ai = is_ai
        title_text = "Manage AI Training Files" if is_ai else "Manage Machine Documents"
        self.setWindowTitle(title_text)
        self.setMinimumSize(650, 480)
        # Forced Text Color Fix
        self.setStyleSheet("""
            ManageDocumentsDialog { background-color: #f0f2f5; }
            QTableWidget { background: white; border-radius: 8px; outline: none; color: black; }
            QTableWidget::item { color: black; padding: 10px; }
            QTableWidget::item:selected { background-color: #e0f2fe; color: black; }
            QHeaderView::section { background-color: #f8fafc; padding: 12px; border: none; border-bottom: 2px solid #cbd5e1; font-weight: 600; color: black; }
            QPushButton { background: #3b82f6; color: white; border-radius: 8px; padding: 12px; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Document Name", "Internal File Path"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add File")
        self.add_btn.clicked.connect(self.add_document)
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet("background: #ef4444;")
        self.del_btn.clicked.connect(self.delete_document)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)
        
        self.load_data()

    def load_data(self):
        docs = db.get_ai_documents() if self.is_ai else db.get_documents()
        self.table.setRowCount(len(docs))
        for row, doc in enumerate(docs):
            self.table.setItem(row, 0, QTableWidgetItem(str(doc["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(doc["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(doc["path"]))

    def add_document(self):
        file_filter = "Data Logs & Documents (*.pdf *.txt *.csv *.log);;All Files (*)" if self.is_ai else "Documents (*.pdf *.jpg *.jpeg *.png);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Document", "", file_filter)
        
        if not file_path: return
            
        default_name = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
        doc_name, ok = QInputDialog.getText(self, "Document Name", "Enter a display name:", text=default_name)
        
        if ok and doc_name.strip():
            assets_dir = config.get_resource_path("assets")
            os.makedirs(assets_dir, exist_ok=True)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(assets_dir, filename)
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path) and os.path.abspath(file_path) != os.path.abspath(dest_path):
                base, ext = os.path.splitext(original_dest)
                dest_path = f"{base}_{counter}{ext}"
                counter += 1
            
            if os.path.abspath(file_path) != os.path.abspath(dest_path):
                shutil.copy2(file_path, dest_path)
            
            success = db.add_ai_document(doc_name.strip(), dest_path) if self.is_ai else db.add_document(doc_name.strip(), dest_path)
            if success: self.load_data()

    def delete_document(self):
        selected = self.table.selectedItems()
        if not selected: return
            
        row = selected[0].row()
        doc_id = self.table.item(row, 0).text()
        doc_path = self.table.item(row, 2).text()
        
        reply = QMessageBox.question(self, 'Confirm', 'Delete this document?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success = db.delete_ai_document(doc_id) if self.is_ai else db.delete_document(doc_id)
            if success:
                try:
                    if os.path.exists(doc_path): os.remove(doc_path)
                except: pass
                self.load_data()

class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        layout = QVBoxLayout(self)
        
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        # Forced Text Color Fix
        self.new_pw.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 14px; color: black; background: white;")
        
        layout.addWidget(QLabel("New Password:"))
        layout.addWidget(self.new_pw)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        
    def save(self):
        if self.new_pw.text():
            config.SIMULATION_PASSWORD = self.new_pw.text()
            self.accept()