from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
    QLabel, QDateTimeEdit, QWidget, QFrame, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

import db
import datetime
import numpy as np
from numpy.polynomial import Polynomial

class LiveGraphDialog(QDialog):
    def __init__(self, display_name, db_column, parent=None):
        super().__init__(parent)
        self.display_name = display_name
        self.db_column = db_column
        self.setWindowTitle(f"Live Graph - {display_name}")
        self.setMinimumSize(900, 700)
        
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLabel { color: #4a5568; font-weight: 600; font-size: 13px; }
            
            QComboBox, QDateTimeEdit, QSpinBox {
                padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px;
                background: white; color: #1e293b; font-size: 13px; outline: none;
            }
            QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus { border: 1px solid #3b82f6; }
            
            QComboBox QAbstractItemView {
                background-color: white; color: #1e293b; border: 1px solid #cbd5e1;
                selection-background-color: #e0f2fe; selection-color: #0f172a; outline: none;
            }
            QComboBox QAbstractItemView::item { min-height: 24px; padding: 4px 8px; }
            
            QSpinBox { width: 80px; }
            QPushButton {
                background-color: #3b82f6; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #94a3b8; }
            
            QPushButton#RefreshBtn { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
            QPushButton#RefreshBtn:hover { background-color: #e2e8f0; color: #1e293b; }
            
            QCheckBox { color: #4a5568; font-weight: bold; font-size: 13px; outline: none; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #cbd5e1; background: white; }
            QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        controls_container = QFrame()
        controls_container.setStyleSheet("QFrame { background: white; border-radius: 8px; border: 1px solid #e2e8f0; }")
        
        main_controls_layout = QVBoxLayout(controls_container)
        main_controls_layout.setContentsMargins(15, 15, 15, 15)
        main_controls_layout.setSpacing(15)
        
        filter_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last Hour", "Last Week", "Last Month", "Last Year", "All Time", "Custom"])
        self.period_combo.view().window().setStyleSheet("background-color: white;")
        self.period_combo.currentIndexChanged.connect(self.on_period_change)
        
        self.start_date = QDateTimeEdit(QDateTime.currentDateTime().addSecs(-3600))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_date.setEnabled(False)
        
        self.end_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_date.setEnabled(False)
        
        filter_layout.addWidget(QLabel("Period:"))
        filter_layout.addWidget(self.period_combo)
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addStretch()
        
        refresh_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("↻ Refresh Now")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_action)
        
        self.auto_refresh_cb = QCheckBox("Auto-Refresh")
        self.auto_refresh_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" sec")
        self.interval_spin.valueChanged.connect(self.update_timer_interval)
        
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.auto_refresh_cb)
        refresh_layout.addWidget(QLabel("Interval:"))
        refresh_layout.addWidget(self.interval_spin)
        
        main_controls_layout.addLayout(filter_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #f1f5f9;")
        main_controls_layout.addWidget(line)
        
        main_controls_layout.addLayout(refresh_layout)
        self.layout.addWidget(controls_container)
        
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        canvas_frame = QFrame()
        canvas_frame.setStyleSheet("QFrame { background: white; border-radius: 8px; border: 1px solid #e2e8f0; }")
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        canvas_layout.addWidget(self.canvas)
        self.layout.addWidget(canvas_frame)
        
        self.ax = self.figure.add_subplot(111)
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(15,15),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round4,pad=0.5", fc="white", ec="#cbd5e1", lw=1, alpha=0.95),
                            arrowprops=dict(arrowstyle="->", color="#475569"))
        self.annot.set_visible(False)
        self.canvas.mpl_connect("motion_notify_event", self.hover)
        
        self.lines = []
        self.scatter_plot = None
        self.current_x_num = []
        self.current_y_val = []
        self.trend_x = None
        self.trend_y = None
        self.cursor_point = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_action)
        
        self.update_graph()

    def sync_preset_dates(self):
        text = self.period_combo.currentText()
        if text == "Custom": return
            
        now = QDateTime.currentDateTime()
        self.end_date.setDateTime(now)
        
        if text == "Last Hour": self.start_date.setDateTime(now.addSecs(-3600))
        elif text == "Last Week": self.start_date.setDateTime(now.addDays(-7))
        elif text == "Last Month": self.start_date.setDateTime(now.addMonths(-1))
        elif text == "Last Year": self.start_date.setDateTime(now.addYears(-1))
        elif text == "All Time": self.start_date.setDateTime(QDateTime(2000, 1, 1, 0, 0))

    def on_period_change(self):
        text = self.period_combo.currentText()
        if text == "Custom":
            self.start_date.setEnabled(True)
            self.end_date.setEnabled(True)
            self.auto_refresh_cb.setChecked(False)
            self.auto_refresh_cb.setEnabled(False)
        else:
            self.start_date.setEnabled(False)
            self.end_date.setEnabled(False)
            self.auto_refresh_cb.setEnabled(True)
            self.sync_preset_dates()
            self.update_graph()

    def refresh_action(self):
        self.sync_preset_dates()
        self.update_graph()

    def toggle_auto_refresh(self):
        if self.auto_refresh_cb.isChecked(): self.timer.start(self.interval_spin.value() * 1000)
        else: self.timer.stop()

    def update_timer_interval(self):
        if self.auto_refresh_cb.isChecked():
            self.timer.setInterval(self.interval_spin.value() * 1000)

    def update_graph(self):
        start = self.start_date.dateTime().toPyDateTime()
        end = self.end_date.dateTime().toPyDateTime()
        
        data = db.get_sensor_history(self.db_column, start, end)
        
        self.ax.clear()
        self.figure.patch.set_facecolor('#ffffff') 
        self.ax.set_facecolor('#ffffff')
        
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#cbd5e1')
        self.ax.spines['bottom'].set_color('#cbd5e1')
        self.ax.tick_params(colors='#64748b', labelsize=10)
        self.ax.grid(color='#f1f5f9', linestyle='--', linewidth=1.5, alpha=0.8)
        
        self.cursor_point, = self.ax.plot([], [], 'o', color='#1d4ed8', markersize=9,
                                           zorder=6, markeredgecolor='white', markeredgewidth=1.5,
                                           visible=False)
        self.trend_x = None
        self.trend_y = None
        
        if not data:
            self.ax.text(0.5, 0.5, "No data available for this period.", 
                         horizontalalignment='center', verticalalignment='center',
                         transform=self.ax.transAxes, color="#64748b", fontsize=12)
            self.canvas.draw()
            return

        times = [row['timestamp'] for row in data]
        values = [row['val'] for row in data]
        
        self.current_x_num = mdates.date2num(times)
        self.current_y_val = np.array(values)
        
        sort_idx = np.argsort(self.current_x_num)
        self.current_x_num = self.current_x_num[sort_idx]
        self.current_y_val = self.current_y_val[sort_idx]
        
        if len(self.current_x_num) >= 2:
            deg = min(3, len(self.current_x_num) - 1)
            p = Polynomial.fit(self.current_x_num, self.current_y_val, deg)
            x_new = np.linspace(self.current_x_num.min(), self.current_x_num.max(), 300)
            y_trend = p(x_new)
            
            line, = self.ax.plot(x_new, y_trend, color='#3b82f6', linewidth=2.5, label="Trend Curve")
            self.lines = [line]
            
            min_y = min(0, self.current_y_val.min() * 0.95)
            self.ax.fill_between(x_new, y_trend, min_y, color='#3b82f6', alpha=0.15)
            
            self.scatter_plot = self.ax.scatter(self.current_x_num, self.current_y_val, 
                                                color='#93c5fd', s=22, zorder=4, alpha=0.65,
                                                edgecolors='white', linewidths=0.8, label="Actual Readings")
            
            self.trend_x = x_new
            self.trend_y = y_trend
            self.ax.legend(loc="upper left", frameon=True, framealpha=0.9, edgecolor="#cbd5e1", fontsize=10)
            
        else:
            self.scatter_plot = self.ax.scatter(self.current_x_num, self.current_y_val, 
                                                color='#93c5fd', s=40, zorder=4, alpha=0.7,
                                                edgecolors='white', linewidths=1.0, label="Actual Readings")
            self.lines = []
            self.ax.legend(loc="upper left", frameon=True, framealpha=0.9, edgecolor="#cbd5e1", fontsize=10)
        
        self.ax.set_title(f"Historical Output: {self.display_name}", color="#1e293b", fontsize=14, fontweight='bold', pad=15)
        self.ax.set_ylabel(self.display_name, color="#475569", fontsize=11, fontweight='bold', labelpad=10)
        
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
        self.figure.autofmt_xdate(rotation=45)
        
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(15,15),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round4,pad=0.5", fc="white", ec="#cbd5e1", lw=1, alpha=0.95),
                            arrowprops=dict(arrowstyle="->", color="#475569"))
        self.annot.set_visible(False)
        
        y_range = self.current_y_val.max() - self.current_y_val.min()
        if y_range == 0: y_range = 1
        self.ax.set_ylim(self.current_y_val.min() - (y_range*0.1), self.current_y_val.max() + (y_range*0.1))
        
        self.canvas.draw()

    def update_annot(self, px, py):
        self.annot.xy = (px, py)
        dt = px if isinstance(px, datetime.datetime) else mdates.num2date(px)
        text = f"{dt.strftime('%H:%M:%S')}\n{py:.2f}"
        self.annot.set_text(text)

    def hover(self, event):
        if event.inaxes != self.ax:
            if self.annot.get_visible() or (self.cursor_point is not None and self.cursor_point.get_visible()):
                self.annot.set_visible(False)
                if self.cursor_point is not None:
                    self.cursor_point.set_visible(False)
                self.canvas.draw_idle()
            return

        if self.scatter_plot is not None:
            cont, ind = self.scatter_plot.contains(event)
            if cont:
                idx = ind["ind"][0]
                px = self.current_x_num[idx]
                py = self.current_y_val[idx]
                self.update_annot(px, py)
                self.annot.set_visible(True)
                if self.cursor_point is not None:
                    self.cursor_point.set_visible(False)
                self.canvas.draw_idle()
                return

        if (self.trend_x is not None and self.cursor_point is not None
                and event.xdata is not None
                and self.trend_x.min() <= event.xdata <= self.trend_x.max()):
            mx = event.xdata
            my = float(np.interp(mx, self.trend_x, self.trend_y))
            self.cursor_point.set_data([mx], [my])
            self.cursor_point.set_visible(True)
            self.update_annot(mx, my)
            self.annot.set_visible(True)
            self.canvas.draw_idle()
            return

        if self.annot.get_visible() or (self.cursor_point is not None and self.cursor_point.get_visible()):
            self.annot.set_visible(False)
            if self.cursor_point is not None:
                self.cursor_point.set_visible(False)
            self.canvas.draw_idle()