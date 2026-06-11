import numpy as np
from scipy.signal import welch
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSplitter
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MonitorPage(QWidget):
    def __init__(self, ble_worker):
        super().__init__()
        self.ble_worker = ble_worker
        self.current_subjek = None
        
        # Buffer Data Sinkronisasi Sinyal
        self.fs = 500  # Frekuensi Sampling ESP32
        self.max_points = self.fs * 3  # Tampilkan jendela waktu 3 detik berjalan
        self.raw_data = [2048] * self.max_points
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Bar Atas Informasi Pasien Aktif
        self.patient_bar = QLabel("Subjek Aktif: Belum Ada Pengujian")
        self.patient_bar.setStyleSheet("background-color: #34495e; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        main_layout.addWidget(self.patient_bar)
        
        # Splitter Layout Utama: Pembagian Area Kiri dan Kanan ala OpenBCI
        splitter_utama = QSplitter(Qt.Horizontal)
        
        # ================= KIRI: PANEL TIME SERIES =================
        panel_kiri = QFrame()
        panel_kiri.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 4px;")
        layout_kiri = QVBoxLayout(panel_kiri)
        
        self.fig_time = Figure(figsize=(6, 5), dpi=90)
        self.canvas_time = FigureCanvas(self.fig_time)
        self.ax_time = self.fig_time.add_subplot(111)
        self.ax_time.set_ylim(0, 4095)
        self.ax_time.set_title("Time Series (Amplitudo ADC)", fontweight="bold", color="#2c3e50")
        self.ax_time.grid(True, alpha=0.3)
        self.line_time, = self.ax_time.plot(self.raw_data, color='#2980b9', lw=1.2)
        self.fig_time.tight_layout()
        
        layout_kiri.addWidget(self.canvas_time)
        splitter_utama.addWidget(panel_kiri)
        
        # ================= KANAN: PANEL FFT & BRAINWAVE BAR =================
        panel_kanan = QSplitter(Qt.Vertical)
        
        # Kanan Atas: FFT Spectrum Plot
        frame_fft = QFrame()
        frame_fft.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 4px;")
        layout_fft = QVBoxLayout(frame_fft)
        self.fig_fft = Figure(figsize=(5, 2.5), dpi=90)
        self.canvas_fft = FigureCanvas(self.fig_fft)
        self.ax_fft = self.fig_fft.add_subplot(111)
        self.ax_fft.set_xlim(0, 60)  # Rentang gelombang EEG 0-60 Hz hobi medis
        self.ax_fft.set_ylim(0, 150)
        self.ax_fft.set_title("FFT Power Spectrum (Domain Frekuensi)", fontweight="bold", color="#2c3e50")
        self.ax_fft.grid(True, alpha=0.3)
        self.line_fft, = self.ax_fft.plot([], [], color='#e67e22', lw=1.2)
        self.fig_fft.tight_layout()
        layout_fft.addWidget(self.canvas_fft)
        panel_kanan.addWidget(frame_fft)
        
        # Kanan Bawah: Welch Power Band Persentase
        frame_bar = QFrame()
        frame_bar.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 4px;")
        layout_bar = QVBoxLayout(frame_bar)
        self.fig_bar = Figure(figsize=(5, 2.5), dpi=90)
        self.canvas_bar = FigureCanvas(self.fig_bar)
        self.ax_bar = self.fig_bar.add_subplot(111)
        self.ax_bar.set_title("Persentase Pita Frekuensi Sinyal Otak", fontweight="bold", color="#2c3e50")
        self.bands_label = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        self.bar_rects = self.ax_bar.bar(self.bands_label, [0]*5, color=['#c0392b','#9b59b6','#1abc9c','#27ae60','#f1c40f'])
        self.ax_bar.set_ylim(0, 100)
        self.fig_bar.tight_layout()
        layout_bar.addWidget(self.canvas_bar)
        panel_kanan.addWidget(frame_bar)
        
        splitter_utama.addWidget(panel_kanan)
        main_layout.addWidget(splitter_utama, 1)
        
        # ================= BOTTOM CONTROLS =================
        ctrl_layout = QHBoxLayout()
        self.status_label = QLabel("Status BLE: Terputus")
        self.status_label.setStyleSheet("font-weight: bold; color: #7f8c8d; font-size:11pt;")
        
        self.start_btn = QPushButton("🔌 Buka Koneksi & Start Stream")
        self.start_btn.clicked.connect(self.start_stream)
        self.start_btn.setStyleSheet("background-color: #056fd9; color: white; font-weight:bold; padding:8px 15px;")
        
        self.stop_btn = QPushButton("🛑 Stop Stream")
        self.stop_btn.clicked.connect(self.stop_stream)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #d35400; color: white; font-weight:bold; padding:8px 15px;")
        
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        main_layout.addLayout(ctrl_layout)

    def start_test(self, subjek_data):
        """Menangkap payload data subjek baru dan merendernya di pojok kiri atas panel"""
        self.current_subjek = subjek_data
        
        # Format string untuk menampilkan Nama Lengkap di pojok kiri atas baris panel
        info_teks = f"Subjek Aktif: {subjek_data['nama'].upper()} " \
                    f"({subjek_data['jenis_kelamin']}, {subjek_data['umur']} Tahun) " \
                    f"| ID: #{subjek_data['id']}"
                    
        self.patient_bar.setText(info_teks)
        
    def start_stream(self):
        self.ble_worker.data_received.connect(self.process_new_data)
        self.ble_worker.status_changed.connect(self.status_label.setText)
        self.ble_worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_stream(self):
        if self.ble_worker:
            self.ble_worker.stop()
            self.ble_worker.wait()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status BLE: Terputus")

    def process_new_data(self, val):
        """Memproses data masuk 500Hz secara realtime tanpa mematikan UI thread"""
        self.raw_data.pop(0)
        self.raw_data.append(val)
        
        # 1. Update Time Series Line Data
        self.line_time.set_ydata(self.raw_data)
        self.canvas_time.draw_idle()
        
        # Mengurangi frekuensi perhitungan FFT/Welch (Hanya dihitung berkala per 25 paket data)
        if val % 25 == 0:
            signal_np = np.array(self.raw_data) - 2048.0 # Normalisasi menghilangkan komponen DC Offset
            N = len(signal_np)
            
            # 2. Update Komputasi Spektrum FFT
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            idx_pos = (fft_freqs >= 0) & (fft_freqs <= 60)
            
            self.line_fft.set_data(fft_freqs[idx_pos], fft_vals[idx_pos])
            # Autoscale dinamis agar visualisasi amplitudo lonjakan terlihat jelas
            if len(fft_vals[idx_pos]) > 0:
                self.ax_fft.set_ylim(0, max(np.max(fft_vals[idx_pos]) * 1.2, 20))
            self.canvas_fft.draw_idle()
            
            # 3. Klasifikasi Pita Gelombang Otak Menggunakan Metode Welch
            try:
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
                        
                    for rect, val_pct in zip(self.bar_rects, percentages):
                        rect.set_height(val_pct)
                    self.canvas_bar.draw_idle()
            except Exception:
                pass