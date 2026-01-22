import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import DownloaderApp

def main():
    try:
        app = QApplication(sys.argv)
        window = DownloaderApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()