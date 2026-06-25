import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

class NullWriter:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

if getattr(sys, 'stdout', None) is None:
    sys.stdout = NullWriter()
if getattr(sys, 'stderr', None) is None:
    sys.stderr = NullWriter()

from PyQt6.QtWidgets import QApplication
import local_server
import config
import main as main_app

def main():
    # Initialize the local database unconditionally to load custom Dashboard configurations.
    local_server.init_local_db()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = main_app.MachineCard()
    window.show()
    
    exit_code = app.exec()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()