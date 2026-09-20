# ui/monitor_page.py

import numpy as np
from scipy.signal import welch, butter, filtfilt
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

        # 2. FFT SPECTRUM PANEL (Sumbu X tetap 60 Hz, sinyal di-filter LPF Cut-Off 45 Hz)
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

        # 3. WELCH BAR CHART PANEL
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
        
        self.bar_rects = self.ax_bar.bar(self.bands_label, [1.0]*5, color=self.bar_colors, edgecolor='none', width=0.6)
        self.ax_bar.set_ylim(0, 100)
        self.ax_bar.grid(True, axis='y', alpha=0.2)
        
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

    def apply_lowpass_filter(self, data, cutoff=45.0, order=4):
        """Membuat dan mengaplikasikan Butterworth Low-Pass Filter pada Cut-Off 45 Hz"""
        nyquist = 0.5 * self.fs
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return filtfilt(b, a, data)

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
        Memutus koneksi BLE, mengalkulasi parameter statistik Rata-Rata, Puncak (Peak), dan Terendah (Trough) Time Series,
        serta frekuensi dan amplitudo tiap gelombang, lalu menyimpan data ke SQLite.
        """
        if self.ble_worker:
            self.ble_worker.stop()
            self.ble_worker.wait()
            
        self.connect_btn.setEnabled(False) 
        self.disconnect_btn.setEnabled(False)
        self.status_label.setText("   Status BLE: Terputus")

        # === 1. INITIALIZE DEFAULT FALLBACK PARAMETERS ===
        delta_p, theta_p, alpha_p, beta_p, gamma_p = 0.0, 0.0, 0.0, 0.0, 0.0
        delta_amp, theta_amp, alpha_amp, beta_amp, gamma_amp = 0.0, 0.0, 0.0, 0.0, 0.0
        
        # Parameter Spesifik Time Series
        max_val = 0.0   # Nilai Puncak Tertinggi (Peak)
        min_val = 0.0   # Nilai Terendah (Trough)
        mean_amp = 0.0  # Nilai Rata-Rata Amplitudo Absolut
        
        amp_50hz = 0.0
        max_freq_band_str = "0.5 - 4"

        # === 2. BRAIN ENGINE: TIME SERIES, SPEKTRAL, FREKUENSI & AMPLITUDO PARSING ===
        if len(self.raw_data) >= 250:
            nilai_tengah_dinamis = np.mean(self.raw_data)
            uV_data_now = [(((x - nilai_tengah_dinamis) / 4095.0) * 3.3 / 1000.0) * 1000000.0 for x in self.raw_data]
            
            # --- CALCULATE TIME SERIES STATISTICS (LANGSUNG DARI SINYAL RIIL) ---
            raw_signal_np = np.array(uV_data_now)
            max_val = float(np.max(raw_signal_np))          # Puncak Tertinggi Positif
            min_val = float(np.min(raw_signal_np))          # Lembah Terendah Negatif
            mean_amp = float(np.mean(np.abs(raw_signal_np))) # Rata-Rata Amplitudo Absolut
            
            try:
                signal_np = self.apply_lowpass_filter(uV_data_now, cutoff=45.0)
            except Exception:
                signal_np = raw_signal_np
                
            N = len(signal_np)
            
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            
            idx_50hz = np.argmin(np.abs(fft_freqs - 50.0))
            amp_50hz = float(fft_vals[idx_50hz]) if len(fft_vals) > idx_50hz else 0.0
            
            # --- HITUNG AMPLITUDO RATA-RATA SPEKTRAL MASING-MASING PITA ---
            bands_hz = {
                "Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 12),
                "Beta": (12, 25), "Gamma": (25, 40)
            }
            amps_dict = {}
            for b_name, (l_hz, h_hz) in bands_hz.items():
                m_idx = (fft_freqs >= l_hz) & (fft_freqs < h_hz)
                amps_dict[b_name] = float(np.mean(fft_vals[m_idx])) if np.any(m_idx) else 0.0
            
            delta_amp = amps_dict["Delta"]
            theta_amp = amps_dict["Theta"]
            alpha_amp = amps_dict["Alpha"]
            beta_amp = amps_dict["Beta"]
            gamma_amp = amps_dict["Gamma"]
            
            idx_valid = (fft_freqs >= 0.5) & (fft_freqs <= 45.0)
            if np.any(idx_valid):
                peak_freq = float(np.abs(fft_freqs[idx_valid][np.argmax(fft_vals[idx_valid])]))
                max_freq_band_str = f"{max(0.5, float(f'{peak_freq - 1.5:.1f}'))} - {float(f'{peak_freq + 1.5:.1f}')}"
            
            try:
                f, psd = welch(signal_np, fs=self.fs, nperseg=min(len(signal_np), self.fs))
                total_power = np.sum(psd[(f >= 0.5) & (f <= 45.0)])
                if total_power > 0:
                    percentages = []
                    for name, (low, high) in bands_hz.items():
                        idx = (f >= low) & (f < high)
                        power_band = np.sum(psd[idx])
                        percentages.append((power_band / total_power) * 100)
                    
                    delta_p, theta_p, alpha_p, beta_p, gamma_p = percentages
            except Exception:
                pass

            # SORTING MULTI-INDIKATOR
            band_info = [
                ("Gelombang Alpha", alpha_p, alpha_amp, "8-12 Hz", "20-80 uV"),
                ("Gelombang Beta", beta_p, beta_amp, "12-25 Hz", "1-5 uV"),
                ("Gelombang Delta", delta_p, delta_amp, "0,5-4 Hz", "100-200 uV"),
                ("Gelombang Gamma", gamma_p, gamma_amp, "25-40 Hz", "0,5-2 uV"),
                ("Gelombang Theta", theta_p, theta_amp, "4-8 Hz", "5-10 uV")
            ]
            
            sorted_bands = sorted(band_info, key=lambda x: (x[1], x[2]), reverse=True)
            proporsi_sorted_str = ", ".join([f"{item[0]} ({item[1]:.1f}%)" for item in sorted_bands])
            
            dom_nama = sorted_bands[0][0]
            dom_hz = sorted_bands[0][3]
            dom_std_amp = sorted_bands[0][4]
            dom_pct = sorted_bands[0][1]
            dom_real_amp = sorted_bands[0][2]
            
            kamus_kondisi_otak = {
                "Gelombang Alpha": "Rileks, beristirahat, tenang, meditasi ringan dan konsentrasi tinggi.",
                "Gelombang Beta": "Keadaan aktif berfikir secara logis, fokus, keadaan sadar penuh, dan berdiskusi.",
                "Gelombang Delta": "Keadaan tidur nyenyak (deep sleep) tanpa mimpi.",
                "Gelombang Gamma": "Aktivitas mental sangat tinggi, rasa takut, panik berlebihan.",
                "Gelombang Theta": "Relaksasi, tidur ringan, bermimpi, kondisi dalam keadaan sadar dan tidak sadar."
            }
            dom_kondisi = kamus_kondisi_otak.get(dom_nama, "kondisi istirahat tertentu.")
            
            dtabg_terdeteksi = [item[0] for item in sorted_bands if item[1] > 1.0]
            dtabg_str = ", ".join(dtabg_terdeteksi)
            noise_pln_ket = "sangat kecil" if amp_50hz < 2.0 else "cukup teredam"

        # === 3. TEMPLATE ANALISIS DENGAN DESKRIPSI TIME SERIES SPESIFIK & AKURAT ===
        paragraf_pakar_otomatis = (
            f"Hasil Analisis dan Interpretasi Sinyal EEG :\n"
            f"• Time Series : Sinyal terdeteksi berada dalam rentang fluktuasi sinyal biologis dengan rata-rata amplitudo sebesar {mean_amp:.1f} uV, amplitudo puncak tertinggi (peak amplitude) sebesar {max_val:.1f} uV, dan amplitudo terendah sebesar {min_val:.1f} uV pada jendela perekaman.\n"
            f"• FFT Plot : Spektrum frekuensi setelah penyaringan LPF Cut-Off 45 Hz menunjukkan akumulasi daya terbesar berada pada rentang frekuensi {max_freq_band_str} Hz. Residu komponen 50 Hz terukur {noise_pln_ket} yaitu {amp_50hz:.2f} uV.\n"
            f"• Pita Frekuensi : Menunjukkan distribusi daya sinyal relatif sebesar Delta ({delta_p:.1f}%), Theta ({theta_p:.1f}%), Alpha ({alpha_p:.1f}%), Beta ({beta_p:.1f}%), dan Gamma ({gamma_p:.1f}%).\n"
            f"• Proporsi Gelombang (dominan ke terendah) : {proporsi_sorted_str}.\n\n"
            f"Kesimpulan :\n"
            f"Berdasarkan hasil analisis spektrum frekuensi dan proporsi gelombang, rekaman sinyal EEG pada subjek terbukti secara valid mengandung komponen {dtabg_str}.\n"
            f"Hasil perekaman menunjukkan bahwa gelombang yang paling dominan pada subjek adalah {dom_nama} (Frekuensi: {dom_hz}, Standar Amplitudo: {dom_std_amp}) dengan kontribusi sebesar {dom_pct:.1f}%. "
            f"Indikasi kondisi otak subjek mengarah pada: {dom_kondisi}"
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
        self.connect_btn.setEnabled(True) 

        # === 6. DIALOG NAVIGASI ===
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
                main_window.switch_page(2) 
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
        """Memproses batch data ADC dengan LPF Cut-off 45 Hz dan tampilan sumbu X 60 Hz."""
        waktu_mulai = time.perf_counter()
        
        for val in values_list:
            self.raw_data.append(val)
            self.packet_counter += 1
            self.dsp_trigger_counter += 1
            if len(self.raw_data) > self.max_points:
                self.raw_data.pop(0)
        
        nilai_tengah_dinamis = np.mean(self.raw_data) if len(self.raw_data) > 0 else 0
        
        TOTAL_GAIN = 1000.0  
        uV_data = [
            (((x - nilai_tengah_dinamis) / 4095.0) * 3.3 / TOTAL_GAIN) * 1000000.0 
            for x in self.raw_data
        ]
        
        self.line_time.set_data(range(len(uV_data)), uV_data)
        self.canvas_time.draw_idle()
        
        dsp_executed = False
        
        if len(self.raw_data) >= 250 and self.dsp_trigger_counter >= 250:
            dsp_executed = True
            self.dsp_trigger_counter = 0  
            
            try:
                signal_np = self.apply_lowpass_filter(uV_data, cutoff=45.0)
            except Exception:
                signal_np = np.array(uV_data)
                
            N = len(signal_np)
            
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            
            idx_pos = (fft_freqs >= 0) & (fft_freqs <= 60.0)
            
            self.line_fft.set_data(fft_freqs[idx_pos], fft_vals[idx_pos])
            if len(fft_vals[idx_pos]) > 0:
                self.ax_fft.set_ylim(0, max(np.max(fft_vals[idx_pos]) * 1.2, 0.1))
            self.canvas_fft.draw_idle()
            
            try:
                f, psd = welch(signal_np, fs=self.fs, nperseg=min(len(signal_np), self.fs))
                idx_eeg = (f >= 0.5) & (f <= 45.0)
                total_power = np.sum(psd[idx_eeg])
                
                if total_power > 0:
                    bands = {"Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 12), "Beta": (12, 25), "Gamma": (25, 40)}
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
                    
                    self.ax_pie.pie(
                        percentages, 
                        labels=self.bands_label, 
                        colors=self.bar_colors, 
                        autopct='%1.1f%%', 
                        startangle=90, 
                        textprops={'fontsize': 8, 'weight': 'bold', 'color': '#334155'}
                    )
                    self.canvas_pie.draw_idle()
            except Exception:
                pass

        waktu_selesai = time.perf_counter()
        latency_ms = (waktu_selesai - waktu_mulai) * 1000
        tipe_proses = "Lengkap (TS + FFT + Welch)" if dsp_executed else "Ringan (Time Series Saja)"
        print(f"⏱️ [PERFORMANCE LOG] Urus Data Batch -> Tipe: {tipe_proses} | Response Time: {latency_ms:.2f} ms")