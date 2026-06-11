# core/ble_worker.py

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakClient, BleakScanner

# Konfigurasi UUID wajib disamakan persis dengan kode ESP32-S3
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" # Karakteristik untuk menulis perintah (Write)
TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" # Karakteristik menerima biner (Notify)

class BLEWorker(QThread):
    data_received = pyqtSignal(int)      # Melemparkan angka desimal ADC hasil ekstrak biner ke UI
    status_changed = pyqtSignal(str)     # Mengirim informasi status ke UI

    def __init__(self):
        super().__init__()
        self.running = False
        self.loop = None
        self.raw_buffer = bytearray()    # Buffer penampung biner streaming gantung

    def run(self):
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_ble())

    async def connect_ble(self):
        self.status_changed.emit("Mencari perangkat ESP32-S3...")
        device = await BleakScanner.find_device_by_name("ESP32S3-ADC")
        
        if not device:
            self.status_changed.emit("Perangkat 'ESP32S3-ADC' tidak ditemukan.")
            return

        self.status_changed.emit("Menghubungkan ke Perangkat...")
        try:
            async with BleakClient(device) as client:
                self.status_changed.emit("Terhubung! Mengonfigurasi Mode...")
                
                # Pemecah & Penyeleksi Data Biner Real-time
                def notification_handler(sender, data):
                    # Gabungkan data biner baru yang masuk ke sisa buffer lama
                    self.raw_buffer.extend(data)
                    
                    # Olah buffer jika panjangnya memenuhi batas minimal paket (6 Byte)
                    while len(self.raw_buffer) >= 6:
                        # Cari header pembuka sinkronisasi [0xC7][0x7C]
                        if self.raw_buffer[0] == 0xC7 and self.raw_buffer[1] == 0x7C:
                            # Pastikan byte terakhir paket adalah END_BYTE [0x01]
                            if self.raw_buffer[5] == 0x01:
                                # Ekstraksi Biner: Gabungkan Byte HI (index 3) dan Byte LO (index 4)
                                hi_byte = self.raw_buffer[3]
                                lo_byte = self.raw_buffer[4]
                                adc_val = (hi_byte << 8) | lo_byte
                                
                                # Kirim nilai desimal ADC (0-4095) ke Monitor Page
                                self.data_received.emit(adc_val)
                                
                                # Potong 6 byte paket yang sudah sukses diproses dari buffer
                                del self.raw_buffer[:6]
                            else:
                                # Jika byte penutup salah, buang 1 byte terdepan untuk mencari ulang sinkronisasi
                                del self.raw_buffer[0]
                        else:
                            # Jika tidak diawali header sync, buang 1 byte terdepan
                            del self.raw_buffer[0]

                # 1. Daftarkan fungsi listener notifikasi ke karakteristik TX ESP32
                await client.start_notify(TX_CHAR_UUID, notification_handler)
                
                # 2. Kirim perintah mengubah output mode ESP32 dari SERIAL ke BOTH agar BLE memancarkan data
                await client.write_gatt_char(RX_CHAR_UUID, b"MODE BOTH\n")
                await asyncio.sleep(0.2) # Jeda waktu singkat untuk pemrosesan perintah di ESP32
                
                # 3. Kirim komando START untuk memicu timer sampling ADC di ISR ESP32
                await client.write_gatt_char(RX_CHAR_UUID, b"START\n")
                self.status_changed.emit("Streaming Data Sinyal Otak Berjalan...")
                
                # Loop menjaga koneksi tetap hidup selama aplikasi aktif
                while self.running:
                    await asyncio.sleep(0.1)
                    
                # 4. Jika tombol STOP diklik, kirim sinyal pemutus transmisi ke ESP32
                await client.write_gatt_char(RX_CHAR_UUID, b"STOP\n")
                await asyncio.sleep(0.1)
                await client.stop_notify(TX_CHAR_UUID)
                self.status_changed.emit("Koneksi Dihentikan.")
                
        except Exception as e:
            self.status_changed.emit(f"Koneksi Putus/Gagal: {str(e)}")

    def stop(self):
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)