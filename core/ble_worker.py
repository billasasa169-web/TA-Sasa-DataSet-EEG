# core/ble_worker.py

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakClient, BleakScanner

class BLEWorker(QThread):
    # Sinyal komunikasi ke UI thread (jika dibutuhkan nantinya)
    data_received = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.loop = None
        self.client = None
        
        # MAC Address Target ESP32-S3 Anda
        self.TARGET_MAC = "B4:3A:45:AD:44:5D"
        
        # UUID Karakteristik TX (Sesuai sketsa Arduino Anda)
        self.SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
        self.TX_UUID      = "6e400003-b5a3-f393-e0a9-e50e24dcca9e" 

    def run(self):
        """Titik masuk thread utama QThread"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        asyncio.ensure_future(self.main_ble_task(), loop=self.loop)
        self.loop.run_forever()

    async def main_ble_task(self):
        self.status_changed.emit("Status BLE: Mencari Perangkat...")
        print("\n================ [CONSOLE.LOG START] ================")
        print(f"Membuka radar scanning untuk mengunci MAC: {self.TARGET_MAC}")
        try:
            device = None
            devices = await BleakScanner.discover(timeout=4.0)
            
            for d in devices:
                if d.address.upper() == self.TARGET_MAC.upper():
                    print(f"🎯 TARGET ESP32-S3 BERHASIL DIKUNCI DI RADAR UDARA!")
                    device = d
                    break
            
            if not device:
                print("❌ GAGAL: Target MAC tidak ditemukan di udara. Pastikan ESP32 menyala.")
                self.status_changed.emit("Status BLE: Perangkat Tidak Ditemukan")
                self.stop_loop()
                return

            self.status_changed.emit("Status BLE: Menyambungkan...")
            
            async with BleakClient(device, disconnected_callback=self.handle_disconnect) as client:
                self.client = client
                self.status_changed.emit("Status BLE: Terhubung")
                print("⚡ [KONEKSI SUKSES] Berhasil Terkoneksi dengan ESP32-S3!")
                print("▶ Menunggu aliran notifikasi paket biner masuk...\n")
                
                # Buka katup aliran notifikasi data biner 14 Byte dari ESP32
                await client.start_notify(self.TX_UUID, self.notification_handler)
                
                # Menjaga loop asinkron agar tetap hidup selama menangkap stream data
                while self.running:
                    await asyncio.sleep(0.1)
                
                await client.stop_notify(self.TX_UUID)
                
        except Exception as e:
            print(f"❌ [ERROR UTAMA BLE]: {e}")
            self.status_changed.emit(f"Status BLE: Eror Koneksi")
        finally:
            self.stop_loop()

    def notification_handler(self, sender, data):
        """
        MEKANISME PEMECAHAN BINER: Mengurai paket batch 14 Byte menjadi 5 data desimal ADC
        dan mencetaknya secara real-time ke terminal konsol.
        """
        # Validasi struktur paket batch: [0xC7][0x7C][Counter] ... [0x01]
        if len(data) == 14 and data[0] == 0xC7 and data[1] == 0x7C and data[13] == 0x01:
            packet_counter = data[2]
            print(f"📦 [RAW BATCH ARRIVED] Counter Paket: {packet_counter} | Hex Array: {data.hex().upper()}")
            
            # Memecah 14 Byte data biner menjadi 5 sampel data ADC 12-bit murni
            for i in range(5):
                high_byte = data[3 + i * 2]
                low_byte = data[3 + i * 2 + 1]
                
                # Operasi bitwise rekonstruksi data integer asli (0-4095)
                adc_value = (high_byte << 8) | low_byte
                
                # Cetak hasil pemecahan biner murni secara real-time ke terminal
                print(f"   └── Sampel ke-{i+1}: {adc_value} (ADC Count)")
                
                # Pancarkan ke UI Thread untuk kebutuhan visualisasi grafik
                self.data_received.emit(adc_value)
        else:
            print(f"⚠️ Paket tidak lolos validasi struktur, panjang: {len(data)} byte.")

    def handle_disconnect(self, client):
        print("⚠️ Perangkat terputus secara mendadak di level OS Windows!")
        self.status_changed.emit("Status BLE: Terputus")
        self.stop_loop()

    def stop_loop(self):
        self.running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            
    def stop(self):
        self.stop_loop()