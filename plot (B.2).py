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
import cProfile
import pstats
import io
import time 

import numpy as np
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

def profile_time_only(func):
    """Decorator untuk mencatat waktu eksekusi murni (ms)"""
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        
        result = func(self, *args, **kwargs)
        
        end_time = time.perf_counter()
        elapsed_time = (end_time - start_time) * 1000 # Konversi ke Milidetik (ms)
        
        class_name = self.__class__.__name__
        # flush=True memaksa teks langsung muncul di terminal saat itu juga
        print(f"📊 {class_name} dirender dalam: {elapsed_time:.4f} ms", flush=True)
        
        return result
    return wrapper

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

    @profile_time_only

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
        
        # 1. Plot Garis (Time Series)
        ax_line = self.canvas_line.axes
        ax_line.clear()
        df_to_plot.plot(ax=ax_line)
        ax_line.set_title("Sinyal Waktu (Time Series)")
        ax_line.set_xlabel("Sampel")
        ax_line.set_ylabel("Amplitudo (μV)")
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

class MainWindow(QMainWindow):
    """
    Jendela Utama Aplikasi (Upload & Kontrol).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analisis Sinyal EEG - PyQt5")
        self.setGeometry(100, 100, 800, 600)

        self.df_data = None
        self.channel_checkboxes = {}
        self.plot_window = None

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # --- BAGIAN 1: INPUT FILE ---
        self.upload_button = QPushButton("Unggah File CSV", self)
        self.upload_button.setStyleSheet("padding: 10px; font-weight: bold;")
        self.upload_button.clicked.connect(self.upload_file)
        self.layout.addWidget(self.upload_button)

        self.status_label = QLabel("Silakan unggah file CSV berisi data sinyal...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        # Tabel Preview Data
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Nama Kolom", "Tipe Data"])
        self.layout.addWidget(self.table_widget)
        
        # --- BAGIAN 2: PEMILIHAN SALURAN ---
        self.channel_groupbox = QGroupBox("Pilih Saluran (Channel)")
        self.channel_layout = QVBoxLayout()
        self.channel_groupbox.setLayout(self.channel_layout)
        self.layout.addWidget(self.channel_groupbox)
        self.channel_groupbox.setEnabled(False)

        # --- BAGIAN 3: KONTROL ANALISIS ---
        self.plot_controls_layout = QHBoxLayout()
        
        self.num_indices_label = QLabel("Jumlah Sampel:")
        self.plot_controls_layout.addWidget(self.num_indices_label)
        
        self.num_indices_input = QLineEdit()
        self.num_indices_input.setPlaceholderText("Kosong = Semua, atau cth: 1000")
        self.plot_controls_layout.addWidget(self.num_indices_input)
        
        self.analyze_button = QPushButton("Mulai Analisis", self)
        self.analyze_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.analyze_button.clicked.connect(self.run_analysis)
        self.analyze_button.setEnabled(False)
        self.plot_controls_layout.addWidget(self.analyze_button)

        self.layout.addLayout(self.plot_controls_layout)

    @profile_time_only

    def upload_file(self, checked=False):
        """Membuka dialog file dan memuat data CSV."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Data", "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)", options=options)

        if file_path:
            try:
                # Membaca CSV
                self.df_data = pd.read_csv(file_path)
                
                # Deteksi otomatis kolom indeks (biasanya Time, Timestamp, ID)
                first_col = self.df_data.columns[0].lower()
                if any(x in first_col for x in ['time', 'date', 'index', 'id', 'timestamp']):
                     self.df_data = pd.read_csv(file_path, index_col=0)

                file_name = file_path.split('/')[-1]
                self.status_label.setText(f"File '{file_name}' berhasil dimuat. ({len(self.df_data)} baris)")
                self.populate_gui_elements()
                self.channel_groupbox.setEnabled(True)
                self.analyze_button.setEnabled(True)
            except Exception as e:
                self.status_label.setText("Gagal membaca file.")
                QMessageBox.critical(self, "Error File", f"Kesalahan saat membaca CSV:\n{e}")

    def populate_gui_elements(self):
        """Membuat checkbox dinamis berdasarkan kolom CSV."""
        self.table_widget.setRowCount(0)
        
        # Hapus widget lama
        for widget in self.channel_checkboxes.values():
            self.channel_layout.removeWidget(widget)
            widget.deleteLater()
        self.channel_checkboxes.clear()

        # Isi tabel dan buat checkbox
        self.table_widget.setRowCount(len(self.df_data.columns))
        for i, (col_name, dtype) in enumerate(self.df_data.dtypes.items()):
            # Isi tabel info
            self.table_widget.setItem(i, 0, QTableWidgetItem(str(col_name)))
            self.table_widget.setItem(i, 1, QTableWidgetItem(str(dtype)))
            
            # Buat checkbox hanya untuk data numerik
            if pd.api.types.is_numeric_dtype(dtype):
                checkbox = QCheckBox(str(col_name))
                # Centang default jika namanya terlihat seperti channel EEG umum
                if str(col_name).lower() in ['fp1', 'fp2', 'cz', 'o1', 'o2', 't3', 't4']:
                    checkbox.setChecked(True)
                self.channel_layout.addWidget(checkbox)
                self.channel_checkboxes[str(col_name)] = checkbox

    def calculate_frequency_percentages(self, df_to_analyze):
        """Menghitung persentase pita frekuensi (Delta, Theta, dll) menggunakan Welch."""
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

    def run_analysis(self):
        """Mengumpulkan input user dan menjalankan visualisasi."""
        selected_channels = [name for name, box in self.channel_checkboxes.items() if box.isChecked()]
        
        if not selected_channels:
            QMessageBox.warning(self, "Peringatan", "Mohon pilih setidaknya satu saluran (channel)!")
            return

        try:
            num_indices_text = self.num_indices_input.text()
            if not num_indices_text:
                df_to_plot = self.df_data[selected_channels]
            else:
                num_indices = int(num_indices_text)
                if num_indices <= 0: raise ValueError
                df_to_plot = self.df_data[selected_channels].head(num_indices)
        except ValueError:
            QMessageBox.critical(self, "Error Input", "Jumlah sampel harus berupa angka positif.")
            return

        # Hitung frekuensi
        band_percentages = self.calculate_frequency_percentages(df_to_plot)
        
        # Buka Jendela Plot
        if self.plot_window is None or not self.plot_window.isVisible():
            self.plot_window = PlotWindow(title="Hasil Visualisasi Sinyal")
        
        self.plot_window.plot_data(df_to_plot, selected_channels, band_percentages)
        self.plot_window.show()
        self.status_label.setText("Analisis selesai. Lihat jendela visualisasi.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 
     