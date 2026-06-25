from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
import db

class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Machine State Logs")
        self.setMinimumSize(550, 400)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["State", "Start Time", "End Time", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        logs = db.get_logs()
        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(str(log["state"]).upper()))
            self.table.setItem(row, 1, QTableWidgetItem(str(log["start_time"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(log["end_time"])))
            self.table.setItem(row, 3, QTableWidgetItem(db.format_runtime(log["duration_seconds"])))