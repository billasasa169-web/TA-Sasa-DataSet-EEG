# core/ble_worker.py

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakClient, BleakScanner

class BLEWorker(QThread):
    data_received = pyqtSignal(list)
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
        self.data_buffer = []
        self.buffer_size = 20

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
                print("▶️ Membuka aliran NOTIFY secara otomatis...")
                
                # Jeda tipis memberikan waktu bagi Windows OS menyusun GATT cache
                await asyncio.sleep(0.5)

                # Buka katup aliran notifikasi data biner 6 Byte langsung
                await client.start_notify(self.TX_UUID, self.notification_handler)
                print("🚀 [ALIRAN DATA AKTIF] Memantau data EEG masuk ke terminal...")
                print("=====================================================\n")
                
                # Menjaga loop asinkron agar tetap hidup selama menangkap stream data otomatis
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
        MEKANISME PEMECAHAN BINER: Mengurai paket tunggal 6 Byte dari ESP32-S3
        dengan optimasi buffer throttling dan kalkulasi Amplitudo (µV) untuk terminal.
        """
        if len(data) == 6 and data[0] == 0xC7 and data[1] == 0x7C and data[5] == 0x01: # 
            packet_counter = data[2] # 
            
            high_byte = data[3] # 
            low_byte = data[4] # 
            adc_value = (high_byte << 8) | low_byte # 
            
            # --- MASUKKAN DATA KE BUFFER TERLEBIH DAHULU ---
            self.data_buffer.append(adc_value) # 
            
            # --- HITUNG AMPLITUDO MIKROVOLT (µV) SECARA REAL-TIME ---
            # Menggunakan rata-rata dari data buffer yang tersedia untuk detrending dinamis
            nilai_tengah_dinamis = sum(self.data_buffer) / len(self.data_buffer)
            
            # Rumus Kalibrasi Medis: ((ADC - Rata_Rata) / 4095.0) * 3.3V / GAIN * 10^6
            TOTAL_GAIN = 1000.0
            amplitudo_uV = (((adc_value - nilai_tengah_dinamis) / 4095.0) * 3.3 / TOTAL_GAIN) * 1000000.0
            
            # CETAK KE TERMINAL (Format pembulatan 1 angka di belakang koma agar rapi)
            # print(f"Paket: {packet_counter} | ADC: {adc_value} | Amplitudo: {amplitudo_uV:.1f} µV")
            
            # Jika buffer sudah mencapai batas ukuran, pancarkan sekaligus ke UI
            if len(self.data_buffer) >= self.buffer_size: # 
                self.data_received.emit(self.data_buffer) # 
                self.data_buffer = [] # Kosongkan kembali buffer untuk batch berikutnya 
                
        else:
            print(f"⚠️ Data Corrupt / Potong | Ukuran: {len(data)} Byte") #

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