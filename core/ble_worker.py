# core/ble_worker.py

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakClient, BleakScanner

class BLEWorker(QThread):
    # Signal untuk berkomunikasi dengan UI Thread
    data_received = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.loop = None
        self.client = None
        
        # UUID Konfigurasi Sinkron Sesuai Firmware ESP32-S3 Anda
        self.TARGET_NAME = "ESP32S3-ADC"
        self.SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
        self.RX_UUID      = "6e400002-b5a3-f393-e0a9-e50e24dcca9e" # Menulis Command ke ESP32
        self.TX_UUID      = "6e400003-b5a3-f393-e0a9-e50e24dcca9e" # Menerima Notification Stream

    def run(self):
        """Titik masuk thread utama QThread"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.main_ble_task())

    async def main_ble_task(self):
        self.status_changed.emit("Status BLE: Mencari Perangkat...")
        try:
            # 1. Scanning Perangkat Terget
            device = await BleakScanner.find_device_by_name(self.TARGET_NAME, timeout=5.0)
            if not device:
                self.status_changed.emit("Status BLE: Perangkat Tidak Ditemukan")
                return

            self.status_changed.emit("Status BLE: Menyambungkan...")
            
            # 2. Inisialisasi Koneksi Client
            async with BleakClient(device) as client:
                self.client = client
                self.status_changed.emit("Status BLE: Terhubung")
                
                # Mengaktifkan listen notification stream data biner dari ESP32
                await client.start_notify(self.TX_UUID, self.notification_handler)
                
                # Mengirimkan Handshake awal agar ESP32 tahu ia harus mengalirkan data ke jalur BLE
                await client.write_gatt_char(self.RX_UUID, b"MODE BLE\n")
                await asyncio.sleep(0.1)
                await client.write_gatt_char(self.RX_UUID, b"START\n")
                
                # Menjaga Loop Asinkron Tetap Hidup Selama Stream Berjalan
                while self.running:
                    await asyncio.sleep(0.1)
                
                # 3. Proses Stop Stream Secara Bersih saat Keluar Sesi
                await client.write_gatt_char(self.RX_UUID, b"STOP\n")
                await client.stop_notify(self.TX_UUID)
                
        except Exception as e:
            self.status_changed.emit(f"Status BLE: Eror Koneksi")
        finally:
            self.status_changed.emit("Status BLE: Terputus")

    def notification_handler(self, sender, data):
        """Membongkar Paket Biner Mentah 6 Byte dari Jalur Komunikasi ESP32"""
        # Validasi Struktur Paket: [C7][7C][CTR][HI][LO][01]
        if len(data) == 6 and data[0] == 0xC7 and data[1] == 0x7C and data[5] == 0x01:
            high_byte = data[3]
            low_byte = data[4]
            
            # Rekonstruksi Bitwise untuk Membentuk Nilai Integer ADC 12-Bit Asli
            adc_value = (high_byte << 8) | low_byte
            
            # Pancarkan Nilai Desimal ke UI Terkait
            self.data_received.emit(adc_value)

    def stop(self):
        """Dipanggil dari UI Thread untuk Menghentikan Proses Transmisi Data"""
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)