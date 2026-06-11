# Script utama untuk aplikasi analisis sinyal EEG dengan PyQt5.
# Fitur:
# - Upload file CSV dengan data sinyal EEG.
# - Deteksi otomatis kolom indeks (Time, Timestamp, ID).
# - Pilih saluran (channel) yang ingin dianalisis.
# - Hitung persentase pita frekuensi (Delta, Theta, Alpha, Beta
#   Gamma) menggunakan metode Welch.
# - Tampilkan 5 plot: Time Series, FFT, Histogram, Pie Chart, dan Topografi Kepala (Topomap).
# - Penanganan error yang kuat untuk berbagai kasus (file, data, plotting).

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.collections # Import penting untuk deteksi titik sensor manual
import numpy as np
import serial
import serial.tools.list_ports
from collections import deque
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QComboBox

from scipy.signal import welch

# PyQt5 Imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QLabel,
                             QTableWidget, QTableWidgetItem, QLineEdit,
                             QGroupBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable

# MNE-Python Imports (dengan penanganan jika library belum diinstal)
try:
    import mne
except ImportError:
    mne = None

class MplCanvas(FigureCanvas):
    """
    Kanvas kustom untuk menanam plot Matplotlib ke dalam PyQt5.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

class PlotWindow(QMainWindow):
    """
    Jendela hasil yang menampilkan 5 plot visualisasi.
    """
    def __init__(self, title="Analisis Data Lengkap", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(150, 150, 1600, 800)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # --- Layout Atas: Line Plot & FFT ---
        top_layout = QHBoxLayout()
        self.canvas_line = MplCanvas(self)
        top_layout.addWidget(self.canvas_line)
        self.canvas_fft = MplCanvas(self)
        top_layout.addWidget(self.canvas_fft)
        self.layout.addLayout(top_layout)

        # --- Layout Bawah: Histogram, Pie Chart, Topografi ---
        bottom_layout = QHBoxLayout()
        self.canvas_hist = MplCanvas(self)
        bottom_layout.addWidget(self.canvas_hist)
        self.canvas_pie = MplCanvas(self)
        bottom_layout.addWidget(self.canvas_pie)
        self.canvas_topo = MplCanvas(self)
        bottom_layout.addWidget(self.canvas_topo)
        self.layout.addLayout(bottom_layout)
        
        # Variabel untuk menyimpan referensi Colorbar agar bisa dihapus nanti
        self.cax_topo = None 

    def _plot_topography(self, ax, band_percentages, selected_channels):
        """
        Fungsi helper untuk memplot topografi kepala (Topomap).
        STRATEGI: Plot peta polos -> Deteksi titik sensor -> Tulis label manual.
        Ini mengatasi masalah kompatibilitas versi MNE dan ukuran font.
        """
        # 1. Bersihkan Area Plot & Colorbar Lama
        ax.clear()
        if self.cax_topo is not None:
            try:
                self.cax_topo.remove()
            except Exception:
                pass
            self.cax_topo = None

        # 2. Cek apakah MNE terinstal
        if mne is None:
            ax.set_title("Library MNE Tidak Ditemukan")
            ax.text(0.5, 0.5, "Fitur ini butuh library MNE.\nInstal: pip install mne", 
                    ha='center', va='center', transform=ax.transAxes, color='red')
            ax.axis('off')
            return

        # 3. Cek data input
        if not selected_channels or not band_percentages:
            ax.set_title("Data Kosong")
            ax.text(0.5, 0.5, "Tidak ada saluran dipilih", 
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            return

        try:
            # --- PERSIAPAN DATA ---
            mapping_data = {}
            for ch in selected_channels:
                val_str = band_percentages[ch].get('Beta', '0%').replace('%', '')
                mapping_data[ch] = float(val_str)
            
            ch_names_input = list(mapping_data.keys())
            
            # Membuat Info object MNE
            info = mne.create_info(ch_names=ch_names_input, sfreq=256, ch_types='eeg')
            
            # --- PENERAPAN MONTASE ---
            montage = mne.channels.make_standard_montage('standard_1020')
            info.set_montage(montage, on_missing='ignore')
            
            # Cek saluran valid (yang punya koordinat)
            valid_indices = []
            valid_names = []
            
            for i, ch_name in enumerate(info.ch_names):
                loc = info['chs'][i]['loc']
                if loc is not None and not np.all(np.isnan(loc[:3])) and np.any(loc[:3]):
                    valid_indices.append(i)
                    valid_names.append(ch_name)

            if not valid_indices:
                ax.set_title("Group Error: Topografi Gagal", color='red', fontweight='bold')
                error_msg = (
                    "TIDAK ADA SALURAN STANDAR DITEMUKAN\n\n"
                    "Cek nama saluran di CSV Anda.\n"
                    "Harus sesuai standar 10-20 (Fp1, Cz, O1, dll)"
                )
                ax.text(0.5, 0.5, error_msg, ha='center', va='center', 
                        transform=ax.transAxes, fontsize=9, 
                        bbox=dict(facecolor='white', alpha=0.9, edgecolor='red'))
                ax.axis('off')
                return

            # --- PLOTTING (Hanya Data Valid) ---
            info_valid = mne.pick_info(info, valid_indices)
            data_valid = np.array([mapping_data[ch] for ch in valid_names])

            nonzero = data_valid[data_valid > 0]
            vmin = np.min(nonzero) if nonzero.size > 0 else 0
            vmax = np.max(data_valid) if data_valid.size > 0 else 1.0
            if np.isclose(vmin, vmax): vmax += 1e-5 

            # --- PLOT PETA (TANPA LABEL NAMA) ---
            # Kita hanya minta MNE gambar peta dan titiknya saja.
            im = None
            base_kwargs = {'axes': ax, 'show': False, 'cmap': 'Reds'}
            
            # Coba Cara Baru (vlim)
            try:
                im, _ = mne.viz.plot_topomap(data_valid, info_valid, **base_kwargs, vlim=(vmin, vmax))
            except TypeError:
                pass
            
            # Coba Cara Lama (vmin/vmax) - Fallback
            if im is None:
                try:
                     im, _ = mne.viz.plot_topomap(data_valid, info_valid, **base_kwargs, vmin=vmin, vmax=vmax)
                except Exception as e:
                     raise e # Jika ini gagal juga, berarti error sistem lain

            # --- MANUAL LABELING (SOLUSI SUPER ROBUST) ---
            # Kita cari titik sensor (scatter plot) yang digambar MNE, lalu kita tempel teks di situ.
            
            # 1. Cek apakah MNE secara ajaib sudah menulis teks? (Versi lama)
            if ax.texts:
                for text_obj in ax.texts:
                    text_obj.set_fontsize(14)
                    text_obj.set_fontweight('bold')
                    text_obj.set_color('black')
            else:
                # 2. Jika belum ada teks (Versi baru/standar), kita cari koordinat titik hitam
                sensor_coords = None
                for collection in ax.collections:
                    # Sensor biasanya berupa PathCollection (titik-titik scatter)
                    if isinstance(collection, matplotlib.collections.PathCollection):
                        offsets = collection.get_offsets()
                        # Validasi: Jumlah titik harus sama dengan jumlah channel
                        if len(offsets) == len(valid_names):
                            sensor_coords = offsets
                            break
                
                # 3. Tulis Teks Manual di Koordinat Sensor
                if sensor_coords is not None:
                    for idx, (x, y) in enumerate(sensor_coords):
                        ax.text(x, y, valid_names[idx], 
                                ha='center', va='center', # Posisi di tengah titik
                                fontsize=14,              # UKURAN FONT (Ganti ini jika kurang besar)
                                fontweight='bold', 
                                color='black')

            ax.set_title(f"Topografi Aktivitas Otak ({len(valid_names)} Ch Valid)")

            # Tambahkan Colorbar
            divider = make_axes_locatable(ax)
            self.cax_topo = divider.append_axes("right", size="5%", pad=0.05)
            self.canvas_topo.fig.colorbar(im, cax=self.cax_topo, label='Power (%)')

        except Exception as e:
            print(f"Critical Topo Error: {e}")
            ax.clear()
            ax.set_title("System Error")
            ax.text(0.5, 0.5, f"Terjadi kesalahan sistem:\n{str(e)}", 
                    ha='center', va='center', transform=ax.transAxes, color='red')
            ax.axis('off')
    
    def plot_data(self, df_to_plot, selected_channels, band_percentages):
        """Memanggil semua fungsi plotting."""
        
        # 1. Plot Garis (Time Series) dengan Moving Average Filter
        ax_line = self.canvas_line.axes
        ax_line.clear()
        
        # --- PENERAPAN MOVING AVERAGE FILTER ---
        window_size = 10  # Ukuran jendela filter. 
                          # Makin besar = makin halus, tapi sinyal asli bisa sedikit tertinggal/berubah bentuk.
                          # Nilai 5 hingga 15 biasanya ideal untuk fs=256Hz.
                          
        # min_periods=1 mencegah munculnya nilai NaN (kosong) di awal grafik
        df_smoothed = df_to_plot.rolling(window=window_size, min_periods=1).mean()
        
        # Plot data yang sudah dihaluskan
        df_smoothed.plot(ax=ax_line)
        
        ax_line.set_title(f"Sinyal Waktu (Time Series) - Filter MA({window_size})")
        ax_line.set_xlabel("Sampel")
        ax_line.set_ylabel("Amplitudo (μV / ADC)")
        ax_line.grid(True, alpha=0.3)
        ax_line.legend(title='Saluran', loc='upper right', fontsize='small')
        self.canvas_line.draw()

        # 2. Plot FFT (Frekuensi)
        ax_fft = self.canvas_fft.axes
        ax_fft.clear()
        N = len(df_to_plot)
        if N > 0:
            for col in df_to_plot.columns:
                data = df_to_plot[col].values
                yf = np.fft.fft(data)
                xf = np.fft.fftfreq(N, 1) # Asumsi fs=1Hz relatif
                
                # Ambil setengah spektrum (positif saja)
                xf_pos = xf[:N//2]
                yf_pos = 2.0/N * np.abs(yf[0:N//2])
                ax_fft.plot(xf_pos, yf_pos, label=col)

        ax_fft.set_title("Spektrum Frekuensi (FFT)")
        ax_fft.set_xlabel("Frekuensi (Hz)")
        ax_fft.set_ylabel("Magnitudo")
        ax_fft.grid(True, alpha=0.3)
        ax_fft.legend(title='Saluran', loc='upper right', fontsize='small')
        self.canvas_fft.draw()
        
        # 3. Plot Histogram
        ax_hist = self.canvas_hist.axes
        ax_hist.clear()
        if band_percentages:
            # Handling kompatibilitas versi Pandas (map vs applymap)
            df_bands = pd.DataFrame(band_percentages).T
            try:
                hist_data = df_bands.map(lambda x: float(x.replace('%', '')))
            except AttributeError:
                hist_data = df_bands.applymap(lambda x: float(x.replace('%', '')))
                
            hist_data.plot(kind='bar', ax=ax_hist, rot=0)
            ax_hist.set_title("Persentase Pita Frekuensi")
            ax_hist.set_ylabel("Persentase (%)")
            ax_hist.grid(axis='y', alpha=0.3)
            ax_hist.legend(title='Pita', fontsize='small')
        else:
            ax_hist.text(0.5, 0.5, 'Tidak ada data', ha='center', va='center')
        self.canvas_hist.draw()

        # 4. Plot Pie Chart
        ax_pie = self.canvas_pie.axes
        ax_pie.clear()
        if band_percentages and selected_channels:
            # Ambil channel pertama sebagai sampel Pie Chart
            main_channel = selected_channels[0]
            pie_vals = band_percentages[main_channel]
            pie_data = pd.Series({k: float(v.replace('%', '')) for k, v in pie_vals.items()})
            
            ax_pie.pie(pie_data, labels=pie_data.index, autopct=lambda pct: f"{pct:.1f}%", startangle=90)
            ax_pie.set_title(f"Proporsi Gelombang: {main_channel}")
        else:
            ax_pie.text(0.5, 0.5, 'Tidak ada data', ha='center', va='center')
        self.canvas_pie.draw()
        
        # 5. Plot Topografi (Dengan Error Handling & Label Manual)
        self._plot_topography(self.canvas_topo.axes, band_percentages, selected_channels)
        self.canvas_topo.draw()

class SerialThread(QThread):
    data_received = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True
        self.serial_conn = None

    def run(self):
        try:
            # Buka koneksi serial
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            
            # --- TAMBAHAN 1: Bersihkan sisa data/sampah saat pertama kali konek ---
            self.serial_conn.reset_input_buffer() 
            
            while self.is_running:
                if self.serial_conn.in_waiting > 0:
                    # --- TAMBAHAN 2: Tambahkan errors='ignore' ---
                    # Ini akan membuang byte yang rusak (seperti 0xf8) tanpa membuat program crash
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        try:
                            # Ubah string "val1,val2" menjadi list float [val1, val2]
                            data = [float(val) for val in line.split(',')]
                            self.data_received.emit(data)
                        except ValueError:
                            # Abaikan baris jika datanya terpotong (misal cuma "204" bukan "2048")
                            pass 
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analisis Sinyal EEG - Realtime ESP32")
        self.setGeometry(100, 100, 800, 600)

        # --- Variabel Real-time ---
        self.max_samples = 1000 # Simpan 1000 data terakhir (rolling buffer)
        self.data_buffer = deque(maxlen=self.max_samples)
        self.channel_names = [] # Akan diisi otomatis saat data pertama masuk
        self.serial_thread = None
        
        # Timer untuk update plot (misal tiap 500 ms)
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots_realtime)

        self.df_data = None
        self.channel_checkboxes = {}
        self.plot_window = None

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # --- BAGIAN 1: KONEKSI ESP32 ---
        serial_layout = QHBoxLayout()
        
        self.port_combo = QComboBox()
        self.refresh_ports()
        serial_layout.addWidget(QLabel("Pilih Port:"))
        serial_layout.addWidget(self.port_combo)
        
        self.refresh_btn = QPushButton("Refresh Port")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("Mulai Koneksi ESP32")
        self.connect_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        serial_layout.addWidget(self.connect_btn)
        
        self.layout.addLayout(serial_layout)

        self.status_label = QLabel("Silakan hubungkan ESP32...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        # --- BAGIAN 2: PEMILIHAN SALURAN ---
        self.channel_groupbox = QGroupBox("Pilih Saluran (Channel)")
        self.channel_layout = QVBoxLayout()
        self.channel_groupbox.setLayout(self.channel_layout)
        self.layout.addWidget(self.channel_groupbox)
        self.channel_groupbox.setEnabled(False)

    def refresh_ports(self):
        """Mencari port COM yang tersedia."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def toggle_connection(self):
        """Mulai atau hentikan koneksi serial."""
        if self.serial_thread is None or not self.serial_thread.is_running:
            port = self.port_combo.currentText()
            if not port:
                QMessageBox.warning(self, "Error", "Port tidak ditemukan!")
                return
            
            # Mulai Thread Serial
            self.serial_thread = SerialThread(port)
            self.serial_thread.data_received.connect(self.receive_data)
            self.serial_thread.error_occurred.connect(self.handle_serial_error)
            self.serial_thread.start()
            
            self.connect_btn.setText("Hentikan Koneksi")
            self.connect_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
            self.status_label.setText(f"Terhubung ke {port}. Menunggu data...")
            
            # Mulai timer update plot (Update setiap 1000 ms / 1 detik)
            self.plot_timer.start(1000) 
        else:
            # Hentikan Thread
            self.serial_thread.stop()
            self.serial_thread = None
            self.plot_timer.stop()
            self.connect_btn.setText("Mulai Koneksi ESP32")
            self.connect_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
            self.status_label.setText("Koneksi dihentikan.")

    def receive_data(self, data):
        """Menerima data dari thread serial dan menyimpannya ke buffer."""
        # Jika ini data pertama, buat nama channel (Fp1, Fp2, dst)
        if not self.channel_names:
            # Beri nama default sesuai jumlah data yang dikirim ESP32
            default_names = ['Fp1', 'Fp2', 'C3', 'C4', 'O1', 'O2']
            self.channel_names = [default_names[i] if i < len(default_names) else f"CH{i+1}" for i in range(len(data))]
            self.populate_gui_elements()
            self.channel_groupbox.setEnabled(True)

        # Masukkan ke buffer
        if len(data) == len(self.channel_names):
            self.data_buffer.append(data)
            self.status_label.setText(f"Menerima data... (Buffer: {len(self.data_buffer)}/{self.max_samples})")

    def handle_serial_error(self, error_msg):
        self.toggle_connection() # Putuskan koneksi
        QMessageBox.critical(self, "Serial Error", f"Terjadi kesalahan koneksi:\n{error_msg}")

    def populate_gui_elements(self):
        """Membuat checkbox dinamis berdasarkan nama channel."""
        for widget in self.channel_checkboxes.values():
            self.channel_layout.removeWidget(widget)
            widget.deleteLater()
        self.channel_checkboxes.clear()

        for col_name in self.channel_names:
            checkbox = QCheckBox(col_name)
            checkbox.setChecked(True) # Centang semua secara default
            self.channel_layout.addWidget(checkbox)
            self.channel_checkboxes[col_name] = checkbox

    def update_plots_realtime(self):
        """Fungsi yang dipanggil oleh QTimer untuk update grafik."""
        if len(self.data_buffer) < 50: # Tunggu sampai data cukup untuk dianalisis
            return

        # Konversi buffer ke Pandas DataFrame agar kompatibel dengan fungsi lama Anda
        self.df_data = pd.DataFrame(list(self.data_buffer), columns=self.channel_names)
        
        selected_channels = [name for name, box in self.channel_checkboxes.items() if box.isChecked()]
        if not selected_channels:
            return

        df_to_plot = self.df_data[selected_channels]

        # Hitung frekuensi (Fungsi lama Anda)
        band_percentages = self.calculate_frequency_percentages(df_to_plot)
        
        # Buka Jendela Plot jika belum terbuka
        if self.plot_window is None or not self.plot_window.isVisible():
            self.plot_window = PlotWindow(title="Real-Time EEG Analysis")
            self.plot_window.show()
        
        # Update plot
        self.plot_window.plot_data(df_to_plot, selected_channels, band_percentages)
    
    def calculate_frequency_percentages(self, df_to_analyze):
        """Menghitung persentase pita frekuensi (Delta, Theta, dll) menggunakan Welch."""
        from scipy.signal import welch
        import numpy as np

        if len(df_to_analyze) < 20: 
            return None

        results = {}
        try:
            fs = 256 # Frekuensi sampling (Default)
            nperseg = min(len(df_to_analyze), fs) 

            for col in df_to_analyze.columns:
                data = df_to_analyze[col].values
                # Hitung Power Spectral Density
                f, psd = welch(data, fs=fs, nperseg=nperseg)
                total_power = np.sum(psd)
                
                if total_power == 0:
                    results[col] = {b: "0.00%" for b in ["Delta", "Theta", "Alpha", "Beta", "Gamma"]}
                    continue

                # Definisi Pita Frekuensi
                bands = {
                    "Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 13),
                    "Beta": (13, 30), "Gamma": (30, 45)
                }
                
                band_percentages = {}
                for band, (low, high) in bands.items():
                    # Integrasi area di bawah kurva untuk pita tertentu
                    idx_band = np.logical_and(f >= low, f < high)
                    power_band = np.sum(psd[idx_band])
                    percentage = (power_band / total_power) * 100
                    band_percentages[band] = f"{percentage:.2f}%"
                
                results[col] = band_percentages
        except Exception as e:
            print(f"Calculation Error: {e}")
            return None
        
        return results

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 
     