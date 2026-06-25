from PyQt6.QtGui import QPixmap
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
import sys
import os
import threading
import local_server
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout,
    QGraphicsDropShadowEffect, QDialog, QSizePolicy, QScrollArea,
    QInputDialog, QLineEdit, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices, QShortcut, QKeySequence
import db
import config
from timelog import LogDialog
from admin import AdminDialog, ChangePasswordDialog
from LiveGraphing import LiveGraphDialog

class DocumentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Machine Documents")
        self.setMinimumSize(320, 400)
        self.setStyleSheet("""
            DocumentDialog { background-color: white; }
            QMessageBox { background-color: white; }
            QMessageBox QLabel { color: #000000; }
            QScrollArea { border: none; background-color: white; }
            QScrollArea > QWidget > QWidget { background-color: white; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Select Document to Open")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #2d3748;")
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        docs = db.get_documents()
        
        if not docs:
            empty_lbl = QLabel("No documents have been added yet.\nGo to the Admin Panel to add some.")
            empty_lbl.setStyleSheet("color: #718096; font-style: italic;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(empty_lbl)
        else:
            for doc in docs:
                btn = QPushButton(doc["name"])
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFont(QFont("Segoe UI", 10))
                btn.setMinimumHeight(45)
                btn.setStyleSheet("""
                    QPushButton { background: #f8fafc; color: #1a202c; border: 1px solid #cbd5e1; border-radius: 6px; }
                    QPushButton:hover { background: #e2e8f0; border-color: #94a3b8; }
                """)
                btn.clicked.connect(lambda checked, p=doc["path"]: self.open_doc(p))
                scroll_layout.addWidget(btn)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def open_doc(self, path):
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            QMessageBox.warning(self, "File Not Found", f"Could not find document at:\n{full_path}")
            return
            
        self.accept()
        main_window = self.parent()
        
        if not hasattr(main_window, 'open_docs'):
            main_window.open_docs = []
            
        for doc in main_window.open_docs:
            try:
                if getattr(doc, 'is_active', False) and getattr(doc, 'file_path', '') == full_path:
                    doc.show()
                    doc.raise_()
                    doc.activateWindow()
                    return
            except RuntimeError: continue
        
        viewer = DocumentViewerDialog(full_path, main_window)
        main_window.open_docs.append(viewer)
        viewer.show()
        main_window.update_dock()
      
class DocumentViewerDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path 
        self.is_active = True 
        self.setWindowTitle(f"Viewing: {os.path.basename(file_path)}")
        self.setMinimumSize(900, 700)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("DocumentViewerDialog { background-color: #f8fafc; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        ext = file_path.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png']:
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #e2e8f0; }")
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setPixmap(QPixmap(file_path))
            scroll_area.setWidget(image_label)
            self.layout.addWidget(scroll_area)
        elif ext == 'pdf':
            if WEB_ENGINE_AVAILABLE:
                self.loading_label = QLabel("Loading PDF document, please wait...")
                self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout.addWidget(self.loading_label)
                QTimer.singleShot(100, self._load_pdf_async)
            else:
                err_label = QLabel("<b>PDF Viewer Missing</b><br><br>Please run <code>pip install PyQt6-WebEngine</code><br>in your terminal.")
                err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout.addWidget(err_label)
        else:
            err_label = QLabel(f"Opened file format: {ext.upper()}.\nContent not visually renderable here.")
            err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(err_label)

    def _load_pdf_async(self):
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PdfViewerEnabled, True)
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.file_path)))
        self.loading_label.deleteLater()
        self.layout.addWidget(self.web_view)

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.setWindowState(Qt.WindowState.WindowNoState)
                self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):
        self.is_active = False
        main_window = self.parent()
        if hasattr(main_window, 'update_dock'): main_window.update_dock()
        super().closeEvent(event)

class DocTab(QFrame):
    def __init__(self, doc_window, parent=None):
        super().__init__(parent)
        self.doc_window = doc_window
        self.setStyleSheet("""
            QFrame { background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 6px; }
            QFrame:hover { background: #cbd5e1; }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(10)
        
        name_str = os.path.basename(doc_window.file_path)
        name_str = os.path.splitext(name_str)[0].replace('_', ' ').title()
        
        lbl = QLabel(name_str)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #334155; border: none; background: transparent;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { color: #64748b; background: transparent; border: none; font-weight: bold; border-radius: 10px; }
            QPushButton:hover { color: white; background: #ef4444; }
        """)
        close_btn.clicked.connect(self.close_tab)
        
        layout.addWidget(lbl)
        layout.addWidget(close_btn)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doc_window.show()
            self.doc_window.raise_()
            self.doc_window.activateWindow()
            
    def close_tab(self):
        self.doc_window.close()

class AdminLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Authentication")
        self.setMinimumWidth(320)
        self.setStyleSheet("AdminLoginDialog { background-color: white; }")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        title = QLabel("Admin Login")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2d3748;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        # Forced Text Color Fix
        self.pw_edit.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; color: black; background: white;")
        layout.addWidget(self.pw_edit)
        
        login_btn = QPushButton("Login")
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton { background: #4a5568; color: white; border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #2d3748; }
        """)
        login_btn.clicked.connect(self.accept)
        layout.addWidget(login_btn)
        
        self.change_pw_btn = QPushButton("Change Password")
        self.change_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_pw_btn.setStyleSheet("color: #3182ce; background: transparent; border: none; text-decoration: underline;")
        self.change_pw_btn.clicked.connect(self.open_change_pw)
        layout.addWidget(self.change_pw_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def open_change_pw(self):
        dlg = ChangePasswordDialog(self)
        dlg.exec()

class MachineCard(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IndustrialGuard — " + config.MACHINE_NAME)
        self.setMinimumSize(750, 600) 
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.sim_thread = None
        self.sim_stop_event = None
        self.is_simulating = False
        self.open_docs = []
        self.sensor_widgets = {} 
        self.component_widgets = {} 
        
        self.setup_ui()
        self.rebuild_ui() 

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(config.POLL_INTERVAL_MS)

        self.fs_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.fs_shortcut.activated.connect(self.toggle_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def setup_ui(self):
        self.setStyleSheet("MachineCard { background-color: #f0f2f5; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        global_header = QHBoxLayout()
        overview_label = QLabel("Dashboard")
        overview_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        overview_label.setStyleSheet("color: #2c3e50;")
        
        self.admin_btn = QPushButton("Admin Options")
        self.admin_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #4a5568; padding: 6px 14px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #2d3748; }
        """)
        self.admin_btn.clicked.connect(self.open_admin_panel)
        
        self.docs_btn = QPushButton("Machine Documents")
        self.docs_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.docs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.docs_btn.setStyleSheet("""
            QPushButton { color: #1a202c; background-color: #e2e8f0; padding: 6px 14px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #cbd5e1; }
        """)
        self.docs_btn.clicked.connect(self.open_dialog)
        
        self.ask_ai_btn = QPushButton("✨ Ask AI")
        self.ask_ai_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.ask_ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask_ai_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #8b5cf6; padding: 6px 14px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        self.ask_ai_btn.clicked.connect(self.open_ask_ai_dialog)

        global_header.addWidget(overview_label)
        global_header.addStretch()
        global_header.addWidget(self.ask_ai_btn)
        global_header.addWidget(self.docs_btn)
        global_header.addWidget(self.admin_btn)
        main_layout.addLayout(global_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollBar:vertical { border: none; background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background-color: #cbd5e1; min-height: 30px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background-color: #94a3b8; }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10) 

        self.machine_card = QFrame()
        self.machine_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.machine_card.setStyleSheet("QFrame#MachineCardFrame { background: white; border-radius: 12px; border: 1px solid #d1d5db; }")
        self.machine_card.setObjectName("MachineCardFrame")

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.machine_card.setGraphicsEffect(shadow)
        
        self.card_root = QVBoxLayout(self.machine_card)
        self.card_root.setSpacing(20)
        self.card_root.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        self.machine_label = QLabel(config.MACHINE_NAME)
        self.machine_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.machine_label.setStyleSheet("color: #1a202c;")

        self.status_badge = QLabel("● RUNNING")
        self.status_badge.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        header.addWidget(self.machine_label)
        header.addStretch()
        header.addWidget(self.status_badge)
        self.card_root.addLayout(header)

        runtime_layout = QHBoxLayout()
        self.runtime_label = QLabel("Run: --   |   Idle: --   |   Breakdown: --")
        self.runtime_label.setFont(QFont("Segoe UI", 12))
        self.runtime_label.setStyleSheet("color: #718096; font-weight: 500;")
        
        self.log_btn = QPushButton("View Logs")
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.setStyleSheet("""
            QPushButton { background: #ebf8ff; color: #3182ce; border: 1px solid #bee3f8; border-radius: 6px; padding: 8px 16px; }
            QPushButton:hover { background: #bee3f8; }
        """)
        self.log_btn.clicked.connect(self.open_log_dialog)

        runtime_layout.addWidget(self.runtime_label)
        runtime_layout.addStretch()
        runtime_layout.addWidget(self.log_btn)
        self.card_root.addLayout(runtime_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        self.card_root.addWidget(line)

        sensor_title = QLabel("Live Readings")
        sensor_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        sensor_title.setStyleSheet("color: #2d3748;")
        self.card_root.addWidget(sensor_title)

        self.sensor_grid = QGridLayout()
        self.sensor_grid.setSpacing(16)
        self.card_root.addLayout(self.sensor_grid)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #e2e8f0;")
        self.card_root.addWidget(line2)

        bitmask_title = QLabel("Component Status")
        bitmask_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        bitmask_title.setStyleSheet("color: #2d3748;")
        self.card_root.addWidget(bitmask_title)

        self.comp_grid = QGridLayout()
        self.comp_grid.setSpacing(16)
        self.card_root.addLayout(self.comp_grid)

        self.scroll_layout.addWidget(self.machine_card)
        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        self.dock_container = QFrame()
        self.dock_container.setStyleSheet("background: white; border-top: 1px solid #cbd5e1;")
        self.dock_container.hide() 
        
        self.dock_layout = QHBoxLayout(self.dock_container)
        self.dock_layout.setContentsMargins(15, 10, 15, 10)
        self.dock_layout.setSpacing(10)
        
        dock_lbl = QLabel("Active Documents:")
        dock_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        dock_lbl.setStyleSheet("color: #4a5568;")
        self.dock_layout.addWidget(dock_lbl)
        self.dock_layout.addStretch()

        root.addWidget(main_content)
        root.addWidget(self.dock_container)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def rebuild_ui(self):
        self._clear_layout(self.sensor_grid)
        self._clear_layout(self.comp_grid)
        self.sensor_widgets.clear()
        self.component_widgets.clear()

        sensor_configs = db.get_sensor_configs()
        for i, s in enumerate(sensor_configs):
            row, col = i // 3, i % 3
            val_label = self._make_sensor_card(s["display_name"], s["db_column"], f"-- {s['unit']}", self.sensor_grid, row, col)
            self.sensor_widgets[s["db_column"]] = {"label": val_label, "unit": s["unit"]}

        comp_configs = db.get_component_configs()
        for i, c in enumerate(comp_configs):
            row, col = i // 4, i % 4
            comp_frame = QFrame()
            comp_frame.setStyleSheet("QFrame { background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }")
            comp_layout = QVBoxLayout(comp_frame)
            comp_layout.setContentsMargins(14, 12, 14, 12)
            
            name = QLabel(c["display_name"])
            name.setFont(QFont("Segoe UI", 11))
            name.setStyleSheet("color: #4a5568; background: transparent; border: none;")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status = QLabel("● OK")
            status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            comp_layout.addWidget(name)
            comp_layout.addWidget(status)
            self.comp_grid.addWidget(comp_frame, row, col)
            
            self.component_widgets[c["db_column"]] = status

        widgets_to_scale = self.findChildren(QLabel) + self.findChildren(QPushButton)
        for widget in widgets_to_scale:
            font = widget.font()
            if font.pointSize() > 0:
                widget.setProperty("base_font_size", font.pointSize())

    def _make_sensor_card(self, display_name, db_column, default, grid, row, col):
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet("QFrame { background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; } QFrame:hover { background: #e2e8f0; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 16, 14, 16)
        label = QLabel(display_name)
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        label.setStyleSheet("color: #64748b; border: none; background: transparent;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value = QLabel(default)
        value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        value.setStyleSheet("border: none; background: transparent; color: #0f172a;")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(value)
        grid.addWidget(frame, row, col)
        
        def on_click(event):
            if event.button() == Qt.MouseButton.LeftButton: self.open_live_graph(display_name, db_column)
        frame.mousePressEvent = on_click
        return value

    def update_dock(self):
        while self.dock_layout.count() > 2:
            item = self.dock_layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
        valid_docs = []
        for doc in self.open_docs:
            try:
                if getattr(doc, 'is_active', False):
                    valid_docs.append(doc)
                    tab = DocTab(doc, self)
                    self.dock_layout.insertWidget(self.dock_layout.count() - 1, tab)
            except RuntimeError: continue
        self.open_docs = valid_docs
        self.dock_container.setVisible(len(self.open_docs) > 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isMinimized() or self.width() < 200 or self.height() < 150: return
        base_width = 800.0
        base_height = 700.0
        scale = min(self.width() / base_width, self.height() / base_height)
        if scale > 1.0: scale = 1.0
        widgets_to_scale = self.findChildren(QLabel) + self.findChildren(QPushButton)
        for widget in widgets_to_scale:
            base_size = widget.property("base_font_size")
            if base_size:
                new_size = max(int(base_size * scale), 6)
                font = widget.font()
                if font.pointSize() != new_size:
                    font.setPointSize(new_size)
                    widget.setFont(font)

    def refresh(self):
        settings = db.get_app_settings()
        data = db.get_machine_data()
        is_offline = not data or (settings["use_local_db"] and not self.is_simulating)
        
        if is_offline:
            self.status_badge.setText("● OFFLINE")
            self.status_badge.setStyleSheet("color: #d93025;")
            for key, widget_info in self.sensor_widgets.items():
                widget_info["label"].setText(f"0 {widget_info['unit']}")
            for key, widget in self.component_widgets.items():
                widget.setText("● OFFLINE")
                widget.setStyleSheet("color: #718096; background: transparent; border: none;")
            return

        state = data.get("state", "").upper()
        if state == "RUNNING":
            self.status_badge.setText("● RUNNING")
            self.status_badge.setStyleSheet("color: #1a9e4a;")
        elif state == "IDLE":
            self.status_badge.setText("● IDLE")
            self.status_badge.setStyleSheet("color: #e6a817;")
        else:
            self.status_badge.setText("● BREAKDOWN")
            self.status_badge.setStyleSheet("color: #d93025;")

        for col_name, widget_info in self.sensor_widgets.items():
            val = data.get(col_name, 0.0)
            widget_info["label"].setText(f"{val} {widget_info['unit']}")

        for col_name, widget in self.component_widgets.items():
            raw_status = data.get(col_name, 0)
            is_ok = (raw_status == 1 or str(raw_status).upper() == 'OK' or raw_status is True)
            if is_ok:
                widget.setText("● OK")
                widget.setStyleSheet("color: #1a9e4a; background: transparent; border: none;")
            else:
                widget.setText("● FAULT")
                widget.setStyleSheet("color: #d93025; background: transparent; border: none;")

        total_run = db.format_runtime(data.get("total_run", 0))
        total_idle = db.format_runtime(data.get("total_idle", 0))
        total_break = db.format_runtime(data.get("total_breakdown", 0))
        self.runtime_label.setText(f"Run: {total_run}   |   Idle: {total_idle}   |   Breakdown: {total_break}")

    def open_dialog(self):
        if hasattr(self, 'docs_menu_dlg') and self.docs_menu_dlg.isVisible():
            self.docs_menu_dlg.raise_()
            self.docs_menu_dlg.activateWindow()
            return
        self.docs_menu_dlg = DocumentDialog(self)
        self.docs_menu_dlg.show()

    def open_log_dialog(self):
        if hasattr(self, 'logs_dlg') and self.logs_dlg.isVisible():
            self.logs_dlg.raise_()
            self.logs_dlg.activateWindow()
            return
        self.logs_dlg = LogDialog(self)
        self.logs_dlg.show()

    def open_admin_panel(self):
        if hasattr(self, 'admin_panel_dlg') and self.admin_panel_dlg.isVisible():
            self.admin_panel_dlg.raise_()
            self.admin_panel_dlg.activateWindow()
            return
        dlg = AdminLoginDialog(self)
        if not dlg.exec(): return
        if dlg.pw_edit.text() != config.SIMULATION_PASSWORD:
            QMessageBox.warning(self, "Access Denied", "Incorrect password.")
            return
        self.admin_panel_dlg = AdminDialog(self, self)
        self.admin_panel_dlg.show()

    def open_live_graph(self, display_name, db_column):
        if not hasattr(self, 'live_graphs'): self.live_graphs = {}
        if db_column in self.live_graphs and self.live_graphs[db_column].isVisible():
            self.live_graphs[db_column].raise_()
            self.live_graphs[db_column].activateWindow()
            return
        dlg = LiveGraphDialog(display_name, db_column, self)
        self.live_graphs[db_column] = dlg
        dlg.show()

    def open_ask_ai_dialog(self):
        from ask_ai_ui import AskAIDialog
        
        if hasattr(self, 'ai_dlg') and self.ai_dlg.isVisible():
            self.ai_dlg.raise_()
            self.ai_dlg.activateWindow()
            return
        
        current_data = db.get_machine_data() or {}
        settings = db.get_app_settings()
        
        is_offline = False
        if settings["use_local_db"] and not self.is_simulating:
            is_offline = True
        elif not settings["use_local_db"] and not current_data:
            is_offline = True

        if is_offline:
            current_data = {"state": "OFFLINE"}
            for s in db.get_sensor_configs():
                current_data[s["db_column"]] = 0.0
            for c in db.get_component_configs():
                current_data[c["db_column"]] = 0
        
        standard_docs = db.get_documents()
        ai_docs = db.get_ai_documents()
        all_docs = standard_docs + ai_docs
        
        self.ai_dlg = AskAIDialog(current_data, all_docs, parent=self)
        self.ai_dlg.show()

    def closeEvent(self, event):
        if self.is_simulating and self.sim_stop_event:
            self.sim_stop_event.set()
            self.sim_thread.join(timeout=1.5)
        event.accept()

    def toggle_simulation(self):
        if self.is_simulating:  
            if self.sim_stop_event: self.sim_stop_event.set()
            self.is_simulating = False
        else:
            self.sim_stop_event = threading.Event()
            self.sim_thread = threading.Thread(target=local_server.simulate, args=(self.sim_stop_event,), daemon=True)
            self.sim_thread.start()
            self.is_simulating = True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MachineCard()
    window.show()
    sys.exit(app.exec())