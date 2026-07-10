# ui/monitor_page.py

import numpy as np
from scipy.signal import welch
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSplitter, QMessageBox
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QBuffer, QIODevice, QByteArray 
import datetime
import time

class MonitorPage(QWidget):
    def __init__(self, ble_worker):
        super().__init__()
        self.ble_worker = ble_worker
        self.current_subjek = None
        
        # SINKRONISASI FREKUENSI SAMPLING (500 Hz)
        self.fs = 500
        self.max_points = self.fs * 10  # 5000 titik data 
        
        self.raw_data = []
        self.packet_counter = 0
        
        # Penampung counter khusus untuk membatasi eksekusi DSP berat (Throttling)
        self.dsp_trigger_counter = 0
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        self.patient_bar = QLabel("Subjek Aktif: Belum Ada Pengujian")
        self.patient_bar.setStyleSheet("background-color: #1e293b; color: white; padding: 10px; font-weight: bold; border-radius: 6px; font-size: 10.5pt;")
        main_layout.addWidget(self.patient_bar)

        # ================= BOTTOM CONTROLS =================
        ctrl_layout = QHBoxLayout()
        self.status_label = QLabel("   Status BLE: Terputus")
        self.status_label.setStyleSheet("font-weight: bold; color: #64748b; font-size:11pt;")
        
        self.connect_btn = QPushButton("🔌 Sambungkan Koneksi")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.connect_hardware)
        self.connect_btn.setStyleSheet("background-color: #16a34a; color: white; font-weight:bold; padding:8px 20px; border:none; border-radius:6px;")
        
        self.disconnect_btn = QPushButton("🛑 Putus Koneksi")
        self.disconnect_btn.setCursor(Qt.PointingHandCursor)
        self.disconnect_btn.clicked.connect(self.disconnect_hardware)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("background-color: #dc2626; color: white; font-weight:bold; padding:8px 20px; border:none; border-radius:6px;")
        
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.connect_btn)
        ctrl_layout.addWidget(self.disconnect_btn)
        main_layout.addLayout(ctrl_layout)

        splitter_vertikal_induk = QSplitter(Qt.Vertical)
        splitter_baris_atas = QSplitter(Qt.Horizontal)
        splitter_baris_bawah = QSplitter(Qt.Horizontal)

        # 1. TIME SERIES PANEL
        frame_time = QFrame()
        frame_time.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_time = QVBoxLayout(frame_time)
        self.fig_time = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_time = FigureCanvas(self.fig_time)
        self.ax_time = self.fig_time.add_subplot(111)
        
        self.ax_time.set_ylim(-200, 200)
        self.ax_time.set_xlim(0, self.max_points)

        posisi_ticks = np.linspace(0, self.max_points, 11)
        label_ticks = ['-10', '-9', '-8', '-7', '-6', '-5', '-4', '-3', '-2', '-1', '0']
        self.ax_time.set_xticks(posisi_ticks)
        self.ax_time.set_xticklabels(label_ticks)
        
        self.ax_time.set_title("time series", fontweight="bold", color="#dc2626", fontsize=12)
        self.ax_time.set_ylabel("amplitudo (µV)", color="#dc2626", fontsize=11, fontweight="bold")
        self.ax_time.set_xlabel("time (s)", color="#dc2626", fontsize=11, fontweight="bold")
        self.ax_time.grid(True, alpha=0.3)
        
        self.line_time, = self.ax_time.plot(self.raw_data, color='#0284c7', lw=1.2)
        self.fig_time.tight_layout()
        layout_time.addWidget(self.canvas_time)
        splitter_baris_atas.addWidget(frame_time)

        # 2. FFT SPECTRUM PANEL
        frame_fft = QFrame()
        frame_fft.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_fft = QVBoxLayout(frame_fft)
        self.fig_fft = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_fft = FigureCanvas(self.fig_fft)
        self.ax_fft = self.fig_fft.add_subplot(111)
        self.ax_fft.set_xlim(0, 60)  
        self.ax_fft.set_ylim(0, 50)
        
        self.ax_fft.set_title("fft plot", fontweight="bold", color="#dc2626", fontsize=12)
        self.ax_fft.set_ylabel("amplitudo (µV)", color="#dc2626", fontsize=11, fontweight="bold")
        self.ax_fft.set_xlabel("frekuensi (Hz)", color="#dc2626", fontsize=11, fontweight="bold")
        self.ax_fft.grid(True, alpha=0.3)
        
        self.line_fft, = self.ax_fft.plot([], [], color='#e67e22', lw=1.2)
        self.fig_fft.tight_layout()
        layout_fft.addWidget(self.canvas_fft)
        splitter_baris_atas.addWidget(frame_fft)

        # 3. WELCH BAR CHART PANEL (OPTIMAL GEOMETRY)
        frame_bar = QFrame()
        frame_bar.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_bar = QVBoxLayout(frame_bar)
        self.fig_bar = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_bar = FigureCanvas(self.fig_bar)
        self.ax_bar = self.fig_bar.add_subplot(111)
        
        self.ax_bar.set_title("presentase pita frekuensi", fontweight="bold", color="#dc2626", fontsize=12)
        self.ax_bar.set_ylabel("persentase (%)", color="#dc2626", fontsize=11, fontweight="bold")
        self.ax_bar.set_xlabel("Ch. 1", color="#dc2626", fontsize=11, fontweight="bold")
        
        self.bands_label = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        self.bar_colors = ['#ef4444', '#a855f7', '#06b6d4', '#22c55e', '#eab308']
        
        # Mengunci objek 5 tiang sejak awal dengan tinggi dasar 1.0 agar layout terbuka kokoh
        self.bar_rects = self.ax_bar.bar(self.bands_label, [1.0]*5, color=self.bar_colors, edgecolor='none', width=0.6)
        self.ax_bar.set_ylim(0, 100)
        self.ax_bar.grid(True, axis='y', alpha=0.2)
        
        # Gunakan margin manual yang stabil, hindari tight_layout di fungsi berulang
        self.fig_bar.subplots_adjust(left=0.15, right=0.95, top=0.88, bottom=0.15)
        
        layout_bar.addWidget(self.canvas_bar)
        splitter_baris_bawah.addWidget(frame_bar)

        # 4. REAL-TIME PIE CHART PANEL
        frame_pie = QFrame()
        frame_pie.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_pie = QVBoxLayout(frame_pie)
        self.fig_pie = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_pie = FigureCanvas(self.fig_pie)
        self.ax_pie = self.fig_pie.add_subplot(111)
        
        self.ax_pie.set_title("proporsi gelombang", fontweight="bold", color="#dc2626", fontsize=12)
        self.ax_pie.axis('off')  
        self.ax_pie.text(0.5, -0.1, "Ch. 1", color="#dc2626", fontsize=11, fontweight="bold",
                         ha='center', va='center', transform=self.ax_pie.transAxes)
    
        self.fig_pie.tight_layout()
        layout_pie.addWidget(self.canvas_pie)
        splitter_baris_bawah.addWidget(frame_pie)

        splitter_vertikal_induk.addWidget(splitter_baris_atas)
        splitter_vertikal_induk.addWidget(splitter_baris_bawah)
        splitter_vertikal_induk.setSizes([400, 400])
        splitter_baris_atas.setSizes([500, 500])
        splitter_baris_bawah.setSizes([500, 500])
        main_layout.addWidget(splitter_vertikal_induk, 1)
        
    def start_test(self, subjek_data):
        self.current_subjek = subjek_data
        info_teks = f"   Subjek Aktif: {subjek_data['nama'].upper()} ({subjek_data['jenis_kelamin']}, {subjek_data['umur']} Tahun) | ID: #{subjek_data['id']}"
        self.patient_bar.setText(info_teks)
        
    def connect_hardware(self):
        self.connect_btn.setEnabled(False)
        try:
            self.ble_worker.data_received.disconnect()
            self.ble_worker.status_changed.disconnect()
        except TypeError:
            pass

        self.ble_worker.data_received.connect(self.process_new_data)
        self.ble_worker.status_changed.connect(self.handle_status_changed)
        self.ble_worker.start()

    def disconnect_hardware(self):
        """
        Memutus koneksi BLE, mengalkulasi parameter isyarat akhir, mengeksekusi sistem pakar
        berdasarkan thresholding dan pola gelombang dominan teoritis, lalu menyimpan data ke SQLite.
        """
        if self.ble_worker:
            self.ble_worker.stop()
            self.ble_worker.wait()
            
        self.connect_btn.setEnabled(False) # Diubah False sesaat agar proses sinkronisasi dialog tenang
        self.disconnect_btn.setEnabled(False)
        self.status_label.setText("   Status BLE: Terputus")

        # === 1. INITIALIZE PARAMETERS ===
        status_alat = "Tidak Diketahui"
        nasihat_klinis = "Rekaman dihentikan mendadak. Data numerik tidak mencukupi untuk inferensi sistem pakar."
        delta_p, theta_p, alpha_p, beta_p, gamma_p = 0.0, 0.0, 0.0, 0.0, 0.0
        max_amp = 0.0
        amp_50hz = 0.0
        teks_deskripsi_dominan = ""

        # === 2. BRAIN ENGINE: SPEKTRAL & FITUR PARSING ===
        if len(self.raw_data) >= 250:
            nilai_tengah_dinamis = np.mean(self.raw_data)
            uV_data_now = [(((x - nilai_tengah_dinamis) / 4095.0) * 3.3 / 1000.0) * 1000000.0 for x in self.raw_data]
            signal_np = np.array(uV_data_now)
            N = len(signal_np)
            
            max_amp = float(np.max(np.abs(signal_np)))
            
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            idx_50hz = np.argmin(np.abs(fft_freqs - 50.0))
            amp_50hz = float(fft_vals[idx_50hz]) if len(fft_vals) > idx_50hz else 0.0
            
            try:
                from scipy.signal import welch
                f, psd = welch(signal_np, fs=self.fs, nperseg=min(len(signal_np), self.fs))
                total_power = np.sum(psd)
                if total_power > 0:
                    bands = {
                        "Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 13),
                        "Beta": (13, 30), "Gamma": (30, 45)
                    }
                    percentages = []
                    for name, (low, high) in bands.items():
                        idx = (f >= low) & (f < high)
                        power_band = np.sum(psd[idx])
                        percentages.append((power_band / total_power) * 100)
                    
                    delta_p, theta_p, alpha_p, beta_p, gamma_p = percentages
            except Exception:
                pass

            # =================================================================================
            # LOGIKA A: EVALUASI KONDISI SISTEM PAKAR BERDASARKAN AMBANG BATAS MULTIDIMENSI
            # =================================================================================
            if max_amp <= 25.0 and amp_50hz < 0.5 and max([delta_p, theta_p, alpha_p, beta_p, gamma_p]) < 40.0:
                status_alat = "Elektroda Terlepas / Mengambang (Floating)"
                nasihat_klinis = "Perangkat dalam kondisi idle. Ujung elektroda menangkap white noise udara bebas karena hambatan input tak terhingga (open circuit)."
                
            elif amp_50hz > 3.5:
                status_alat = "Kontaminasi Interferensi Frekuensi Daya Jaringan (Power Line Interference)"
                nasihat_klinis = "Sinyal terdistorsi total oleh Derau Hum Jaringan Listrik AC (50 Hz) akibat induksi elektromagnetik ruangan. Data EEG biologis tenggelam."
                
            elif delta_p > 70.0:
                status_alat = "Artefak Motorik Ekstrem (Kedipan/Gerak Otot)"
                nasihat_klinis = "Rekaman terdistorsi oleh artefak biologis non-otak, dipicu oleh aktivitas kedipan mata (EOG), gerakan kepala, atau peregangan otot rahang (EMG)."
                
            elif beta_p > 25.0 or gamma_p > 25.0:
                status_alat = "Subjek Fokus / Terjaga & Mata Terbuka"
                nasihat_klinis = "Subjek dalam kondisi sadar penuh, membuka mata, aktif secara kognitif, atau sedang memproses informasi visual dan berpikir aktif."
                
            elif alpha_p > 30.0:
                status_alat = "Subjek Rileks / Meditasi (Mata Tertutup)"
                nasihat_klinis = "Subjek dalam kondisi rileksasi mental tingkat tinggi, tenang, tidak berpikir berat, dan menutup mata tanpa tertidur (Alpha blocking state)."
                
            else:
                status_alat = "Subjek Mengantuk Berat / Penurunan Kognitif"
                nasihat_klinis = "Subjek berada dalam fase kantuk berat, kelelahan mental yang ekstrem, atau transisi menuju fase tidur awal (NREM stage 1)."

            # =================================================================================
            # LOGIKA B: DETEKSI PITA GELOMBANG DOMINAN BERDASARKAN DATA RIIL (SESUAI GAMBAR RUJUKAN)
            # =================================================================================
            band_names = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
            band_values = [delta_p, theta_p, alpha_p, beta_p, gamma_p]
            
            # Cari indeks dengan nilai persentase tertinggi
            idx_dominan = int(np.argmax(band_values))
            nama_dominan = band_names[idx_dominan]
            
            # Kamus Pemetaan Deskripsi Analisis Fisiologis (Sesuai Gambar Rujukan Anda)
            kamus_analisis_teoritis = {
                "Alpha": "Dominasi nilai Alpha pada Persentase Pita Frekuensi menunjukkan karakteristik aktivitas otak yang umumnya muncul pada kondisi istirahat. Gelombang ini (8-13 Hz) umumnya berkaitan dengan kondisi relaksasi, ketenangan, dan berkurangmya rangsangan visual, terutama saat mata tertutup.",
                "Beta": "Dominasi nilai Beta pada Persentase Pita Frekuensi menunjukkan aktivitas otak yang relatif aktif. Gelombang ini (13-30 Hz) umumnya berkaitan dengan kondisi aktif berfikir secara logis, fokus, berdiskusi, dan keadaan dalam kesadaran penuh.",
                "Delta": "Dominasi nilai Delta pada Persentase Pita Frekuensi menunjukkan gelombang yang dominan. Gelombang ini (0,5-4 Hz) umumnya muncul pada saat tidur nyenyak (deep sleep). Apabila dominan saat subjek dalam keadaan sadar, hasil perlu diinterpretasikan secara hati-hati karena dapat dipengaruhi oleh berbagai faktor, termasuk artefak.",
                "Gamma": "Dominasi nilai Gamma pada Persentase Pita Frekuensi menunjukkan gelombang yang dominan. Gelombang ini (30-100 Hz) umumnya dikaitkan dengan konsenterasi tinggi, pemrosesan informasi, pembelajaran dan pemrosesan kognitif yang kompleks.",
                "Theta": "Dominasi nilai Theta pada Persentase Pita Frekuensi menunjukkan karakteristik aktivitas otak yang sering muncul pada kondisi tersebut. Gelombang ini (4-8 Hz) umumnya berkaitan dengan kondisi relaksasi yang lebih dalam, mengantuk, tahap awal tidur, kondisi keadaan bawah sadar."
            }
            
            teks_deskripsi_dominan = kamus_analisis_teoritis.get(nama_dominan, "")

        # 3. SUSUN TOTAL PARAGRAF REKAM MEDIS UNTUK SQLITE & PDF
        paragraf_pakar_otomatis = (
            f"Berdasarkan hasil uji pengkondisian matriks isyarat, status rekaman diidentifikasi sebagai: {status_alat.upper()}.\n\n"
            f"Indikator Parameter Fisik:\n"
            f"- Amplitudo Isyarat (Time Series): Rentang puncak tertinggi terdeteksi di skala {max_amp:.1f} uV.\n"
            f"- Pola Spektrum (FFT Plot): Magnitudo pada komponen Interferensi Frekuensi Daya Jaringan 50 Hz berada di nilai {amp_50hz:.2f} uV.\n"
            f"- Distribusi Welch PSD (Pita Frekuensi): Delta {delta_p:.1f}%, Theta {theta_p:.1f}%, Alpha {alpha_p:.1f}%, Beta {beta_p:.1f}%, Gamma {gamma_p:.1f}%.\n\n"
            f"Kesimpulan Interpretasi Alat:\n"
            f"{nasihat_klinis}\n\n"
            f"Deskripsi Analisis Fisiologis:\n"
            f"{teks_deskripsi_dominan}"
        )

        # === 4. SCREENSHOT PANEL & SIMPAN BLOB KE SQLITE ===
        splitter_grafik = self.findChild(QSplitter)
        if splitter_grafik and self.current_subjek:
            from PyQt5.QtGui import QPixmap
            from PyQt5.QtCore import QBuffer, QIODevice, QByteArray
            import datetime
            
            screenshot = splitter_grafik.grab()
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            screenshot.save(buffer, "PNG")
            blob_gambar = byte_array.data()
            
            subjek_id = self.current_subjek['id']
            tanggal_sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                self.window().db_manager.simpan_riwayat_grafik(subjek_id, tanggal_sekarang, blob_gambar, paragraf_pakar_otomatis)
                print("✅ [AUTO-SAVE SUCCESS] Data grafik dan hasil analisis komprehensif dikunci ke SQLite.")
            except Exception as e:
                print(f"⚠️ Gagal menyimpan screenshot ke SQLite: {e}")

        # === 5. ENVIRONMENT RESET ===
        self.raw_data = []
        self.packet_counter = 0
        self.dsp_trigger_counter = 0
        self.connect_btn.setEnabled(True) # Aktifkan kembali tombol pasca-proses tuntas

        # === 6. DIALOG NAVIGASI INTERAKTIF FIX ===
        tanya_pindah = QMessageBox(self)
        tanya_pindah.setIcon(QMessageBox.Information)
        tanya_pindah.setWindowTitle("Koneksi Diputus")
        tanya_pindah.setText("Koneksi Bluetooth telah berhasil diputus.\nIngin cek hasil rekaman?")
        tanya_pindah.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        tanya_pindah.button(QMessageBox.Cancel).setText("Tutup")
        
        pilihan = tanya_pindah.exec_()
        
        if pilihan == QMessageBox.Ok:
            main_window = self.window()
            if main_window and hasattr(main_window, 'switch_page'):
                main_window.switch_page(2) # Pindah halaman secara resmi via fungsi switch_page main_window.py
        else:
            print("ℹ️ Operator memilih tetap berada di halaman monitoring.")

    def handle_status_changed(self, text):
        self.status_label.setText(text)
        if "Terputus" in text or "Tidak Ditemukan" in text or "Eror" in text:
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
        elif "Terhubung" in text:
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)

    def process_new_data(self, values_list):
        """
        Memproses batch data ADC dengan pengujian latency komputasi dan rendering.
        """
        # KUNCI LATENCY START: Catat waktu tepat saat batch data masuk dari BLEWorker
        waktu_mulai = time.perf_counter()
        
        # 1. MEKANISME SLIDING WINDOW
        for val in values_list:
            self.raw_data.append(val)
            self.packet_counter += 1
            self.dsp_trigger_counter += 1
            if len(self.raw_data) > self.max_points:
                self.raw_data.pop(0)
        
        # 2. PROSES DETRENDING
        nilai_tengah_dinamis = np.mean(self.raw_data) if len(self.raw_data) > 0 else 0
        
        # 3. KONVERSI DIREK KE MIKROVOLT
        TOTAL_GAIN = 1000.0  
        uV_data = [
            (((x - nilai_tengah_dinamis) / 4095.0) * 3.3 / TOTAL_GAIN) * 1000000.0 
            for x in self.raw_data
        ]
        
        # 4. UPDATE GRAPH REAL-TIME (Time Series)
        self.line_time.set_data(range(len(uV_data)), uV_data)
        self.canvas_time.draw_idle()
        
        # Indikator pembantu untuk mencatat apakah blok DSP berat ikut dieksekusi
        dsp_executed = False
        
        # 5. EKSEKUSI DSP BERAT (Setiap 250 sampel)
        if len(self.raw_data) >= 250 and self.dsp_trigger_counter >= 250:
            dsp_executed = True
            self.dsp_trigger_counter = 0  
            
            signal_np = np.array(uV_data)
            N = len(signal_np)
            
            # Perhitungan FFT SPECTRUM
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            idx_pos = (fft_freqs >= 0) & (fft_freqs <= 60)
            
            self.line_fft.set_data(fft_freqs[idx_pos], fft_vals[idx_pos])
            if len(fft_vals[idx_pos]) > 0:
                self.ax_fft.set_ylim(0, max(np.max(fft_vals[idx_pos]) * 1.2, 0.1))
            self.canvas_fft.draw_idle()
            
            # Perhitungan WELCH PSD & PIE CHART
            try:
                f, psd = welch(signal_np, fs=self.fs, nperseg=min(len(signal_np), self.fs))
                total_power = np.sum(psd)
                if total_power > 0:
                    bands = {"Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 13), "Beta": (13, 30), "Gamma": (30, 45)}
                    percentages = []
                    for name, (low, high) in bands.items():
                        idx = (f >= low) & (f < high)
                        power_band = np.sum(psd[idx])
                        percentages.append((power_band / total_power) * 100)
                    
                    for rect, val_pct in zip(self.bar_rects, percentages):
                        rect.set_height(val_pct)
                    self.canvas_bar.draw_idle()
                    
                    self.ax_pie.clear() 
                    self.ax_pie.set_title("proporsi gelombang", fontweight="bold", color="#dc2626", fontsize=12)
                    self.ax_pie.axis('off') 
                    self.ax_pie.text(0.5, -0.1, "Ch. 1", color="#dc2626", fontsize=11, fontweight="bold", ha='center', va='center', transform=self.ax_pie.transAxes)
                    self.ax_pie.pie(percentages, labels=self.bands_label, colors=self.bar_colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8, 'weight': 'bold', 'color': '#334155'})
                    self.canvas_pie.draw_idle()
            except Exception:
                pass

        # KUNCI LATENCY END: Hitung selisih waktu eksekusi
        waktu_selesai = time.perf_counter()
        latency_ms = (waktu_selesai - waktu_mulai) * 1000
        
        # Cetak log hasil ke terminal untuk kebutuhan pengujian data Bab 4 skripsi
        tipe_proses = "Lengkap (TS + FFT + Welch)" if dsp_executed else "Ringan (Time Series Saja)"
        print(f"⏱️ [PERFORMANCE LOG] Urus Data Batch -> Tipe: {tipe_proses} | Response Time: {latency_ms:.2f} ms")