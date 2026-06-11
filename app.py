import sys
from PyQt5.QtWidgets import QApplication
from database.db_manager import DBManager
from core.ble_worker import BLEWorker
from ui.main_window import MainWindow

def main():
    # 1. Inisialisasi Core Application Engine
    app = QApplication(sys.argv)
    
    # 2. Inisialisasi Manajer Database SQLite Lokal
    db_manager = DBManager()
    
    # 3. Inisialisasi Thread Komunikasi Radio BLE Bluetooth
    ble_worker = BLEWorker()
    
    # 4. Bangun Frame GUI Utama Aplikasi Desktop
    main_gui = MainWindow(db_manager, ble_worker)
    main_gui.show()
    
    # 5. Kunci Loop Sistem Operasi
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()