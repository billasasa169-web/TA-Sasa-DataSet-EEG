# ui/monitor_page.py

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
        
        # Counter internal untuk membatasi frekuensi kalkulasi matematika berat (FFT/Welch)
        self.packet_counter = 0
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Bar Atas Informasi Pasien Aktif
        self.patient_bar = QLabel("Subjek Aktif: Belum Ada Pengujian")
        self.patient_bar.setStyleSheet("background-color: #1e293b; color: white; padding: 10px; font-weight: bold; border-radius: 6px; font-size: 10.5pt;")
        main_layout.addWidget(self.patient_bar)
        
        # ================= STRUKTUR LAYOUT UTAMA: 4 KUADRAN GRID SPLITTER =================
        splitter_vertikal_induk = QSplitter(Qt.Vertical)
        splitter_baris_atas = QSplitter(Qt.Horizontal)
        splitter_baris_bawah = QSplitter(Qt.Horizontal)

        # ---------------- 1. KIRI ATAS: TIME SERIES PANEL ----------------
        frame_time = QFrame()
        frame_time.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_time = QVBoxLayout(frame_time)
        
        self.fig_time = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_time = FigureCanvas(self.fig_time)
        self.ax_time = self.fig_time.add_subplot(111)
        self.ax_time.set_ylim(0, 4095)
        self.ax_time.set_title("Time Series (Amplitudo ADC)", fontweight="bold", color="#1e293b", fontsize=10)
        self.ax_time.grid(True, alpha=0.3)
        self.line_time, = self.ax_time.plot(self.raw_data, color='#0284c7', lw=1.2)
        self.fig_time.tight_layout()
        
        layout_time.addWidget(self.canvas_time)
        splitter_baris_atas.addWidget(frame_time)

        # ---------------- 2. KANAN ATAS: FFT SPECTRUM PANEL ----------------
        frame_fft = QFrame()
        frame_fft.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_fft = QVBoxLayout(frame_fft)
        
        self.fig_fft = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_fft = FigureCanvas(self.fig_fft)
        self.ax_fft = self.fig_fft.add_subplot(111)
        self.ax_fft.set_xlim(0, 60)  
        self.ax_fft.set_ylim(0, 150)
        self.ax_fft.set_title("FFT Power Spectrum (Domain Frekuensi)", fontweight="bold", color="#1e293b", fontsize=10)
        self.ax_fft.grid(True, alpha=0.3)
        self.line_fft, = self.ax_fft.plot([], [], color='#e67e22', lw=1.2)
        self.fig_fft.tight_layout()
        
        layout_fft.addWidget(self.canvas_fft)
        splitter_baris_atas.addWidget(frame_fft)

        # ---------------- 3. KIRI BAWAH: WELCH BAR CHART PANEL ----------------
        frame_bar = QFrame()
        frame_bar.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_bar = QVBoxLayout(frame_bar)
        
        self.fig_bar = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_bar = FigureCanvas(self.fig_bar)
        self.ax_bar = self.fig_bar.add_subplot(111)
        self.ax_bar.set_title("Persentase Pita Frekuensi Sinyal Otak", fontweight="bold", color="#1e293b", fontsize=10)
        self.bands_label = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        self.bar_colors = ['#ef4444', '#a855f7', '#06b6d4', '#22c55e', '#eab308']
        self.bar_rects = self.ax_bar.bar(self.bands_label, [0]*5, color=self.bar_colors, edgecolor='none', width=0.6)
        self.ax_bar.set_ylim(0, 100)
        self.ax_bar.grid(True, axis='y', alpha=0.2)
        self.fig_bar.tight_layout()
        
        layout_bar.addWidget(self.canvas_bar)
        splitter_baris_bawah.addWidget(frame_bar)

        # ---------------- 4. KANAN BAWAH: REAL-TIME PIE CHART PANEL ----------------
        frame_pie = QFrame()
        frame_pie.setStyleSheet("background-color: white; border: 1px solid #cbd5e1; border-radius: 6px;")
        layout_pie = QVBoxLayout(frame_pie)
        
        self.fig_pie = Figure(figsize=(5, 3.5), dpi=90)
        self.canvas_pie = FigureCanvas(self.fig_pie)
        self.ax_pie = self.fig_pie.add_subplot(111)
        self.ax_pie.set_title("Distribusi Gelombang Otak", fontweight="bold", color="#1e293b", fontsize=10)
        self.fig_pie.tight_layout()
        
        layout_pie.addWidget(self.canvas_pie)
        splitter_baris_bawah.addWidget(frame_pie)

        # Gabungkan kompartemen splitter
        splitter_vertikal_induk.addWidget(splitter_baris_atas)
        splitter_vertikal_induk.addWidget(splitter_baris_bawah)
        splitter_vertikal_induk.setSizes([400, 400])
        splitter_baris_atas.setSizes([500, 500])
        splitter_baris_bawah.setSizes([500, 500])
        
        main_layout.addWidget(splitter_vertikal_induk, 1)
        
        # ================= BOTTOM CONTROLS =================
        ctrl_layout = QHBoxLayout()
        self.status_label = QLabel("   Status BLE: Terputus")
        self.status_label.setStyleSheet("font-weight: bold; color: #64748b; font-size:11pt;")
        
        self.start_btn = QPushButton("🔌 Buka Koneksi & Start Stream")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_stream)
        self.start_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight:bold; padding:10px 20px; border:none; border-radius:6px;")
        
        self.stop_btn = QPushButton("🛑 Stop Stream")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight:bold; padding:10px 20px; border:none; border-radius:6px;")
        
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        main_layout.addLayout(ctrl_layout)

    def start_test(self, subjek_data):
        self.current_subjek = subjek_data
        info_teks = f"   Subjek Aktif: {subjek_data['nama'].upper()} ({subjek_data['jenis_kelamin']}, {subjek_data['umur']} Tahun) | ID: #{subjek_data['id']}"
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
        
        # Increment counter paket data masuk
        self.packet_counter += 1
        
        # 1. Update Grafik Utama Time Series (Kiri Atas) - Berjalan Real-time di setiap titik data masuk
        self.line_time.set_ydata(self.raw_data)
        self.canvas_time.draw_idle()
        
        # PERBAIKAN: Gunakan self.packet_counter untuk pembatasan beban komputasi FFT/Welch (Per 25 data paket)
        if self.packet_counter % 25 == 0:
            signal_np = np.array(self.raw_data) - 2048.0 
            N = len(signal_np)
            
            # 2. Update FFT Power Spectrum (Kanan Atas)
            fft_vals = np.abs(np.fft.fft(signal_np)) / N
            fft_freqs = np.fft.fftfreq(N, 1/self.fs)
            idx_pos = (fft_freqs >= 0) & (fft_freqs <= 60)
            
            self.line_fft.set_data(fft_freqs[idx_pos], fft_vals[idx_pos])
            if len(fft_vals[idx_pos]) > 0:
                self.ax_fft.set_ylim(0, max(np.max(fft_vals[idx_pos]) * 1.2, 20))
            self.canvas_fft.draw_idle()
            
            # 3. Komputasi Metode Welch untuk Klasifikasi Pita Gelombang Otak
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
                    
                    # 3.1. Update Welch Bar Chart (Kiri Bawah)
                    for rect, val_pct in zip(self.bar_rects, percentages):
                        rect.set_height(val_pct)
                    self.canvas_bar.draw_idle()
                    
                    # 3.2. Update Visualisasi Pie Chart (Kanan Bawah) secara Real-time
                    self.ax_pie.clear() 
                    self.ax_pie.set_title("Distribusi Gelombang Otak (Pie)", fontweight="bold", color="#1e293b", fontsize=10)
                    
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