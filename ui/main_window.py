import datetime
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTableWidget, QTableWidgetItem, QTabWidget, 
                             QGroupBox, QHeaderView, QSplitter, QMenu, QAction,
                             QApplication, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices
from core.manager import PlatformManager
from core.downloader import DownloadWorker

# --- Constants ---
# User preferred color
ACCENT_COLOR = "#032EA1"
TEXT_COLOR_ON_ACCENT = "#FFFFFF"

class DownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SDM - Downloader Manager")
        self.resize(1200, 800)
        
        self.platform_manager = PlatformManager()
        self.active_downloads = {} # row_id: DownloadWorker
        
        # Apply Global Theme (Light Mode with Custom Accent)
        self.apply_theme()

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main Layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Row 1: Tabs (Downloader, Settings) ---
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Create Tab Content
        self.downloader_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs.addTab(self.downloader_tab, "Downloader")
        self.tabs.addTab(self.settings_tab, "Settings")

        # Setup Downloader Tab Layout (Rows 2-6)
        self.setup_downloader_ui()
        
        # Setup Settings Tab (Placeholder)
        self.setup_settings_ui()

    def apply_theme(self):
        """Applies the light theme and custom accent colors."""
        app_style = f"""
            QMainWindow {{
                background-color: #F0F0F0;
            }}
            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: {TEXT_COLOR_ON_ACCENT};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #043BB5;
            }}
            QPushButton:pressed {{
                background-color: #022075;
            }}
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                selection-background-color: {ACCENT_COLOR};
                gridline-color: #EEEEEE;
            }}
            QHeaderView::section {{
                background-color: {ACCENT_COLOR};
                color: {TEXT_COLOR_ON_ACCENT};
                padding: 4px;
                border: 1px solid #022075;
            }}
            QLabel {{
                color: #333333;
            }}
            QGroupBox {{
                border: 1px solid #CCCCCC;
                margin-top: 20px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
        """
        self.setStyleSheet(app_style)

    def setup_downloader_ui(self):
        layout = QVBoxLayout(self.downloader_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Row 2: Header Info ---
        row2_layout = QHBoxLayout()
        
        self.logo_label = self.create_placeholder_logo("Logo", 50, 50, Qt.darkGray)
        row2_layout.addWidget(self.logo_label)

        self.ping_label = QLabel("Ping: 24ms")
        self.user_label = QLabel("User: Admin")
        self.timer_label = QLabel("00:00:00")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        row2_layout.addWidget(self.ping_label)
        row2_layout.addSpacing(20)
        row2_layout.addWidget(self.user_label)
        row2_layout.addSpacing(20)
        row2_layout.addWidget(self.timer_label)

        row2_layout.addStretch()

        self.btn_checkup = QPushButton("Checkup")
        self.btn_license = QPushButton("License")
        row2_layout.addWidget(self.btn_checkup)
        row2_layout.addWidget(self.btn_license)

        layout.addLayout(row2_layout)

        # --- Row 3: Input & Actions ---
        row3_layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        self.url_input.setStyleSheet("padding: 8px; border: 1px solid #CCC; border-radius: 4px;")
        
        self.btn_add_url = QPushButton("Add URL")
        self.btn_scrap = QPushButton("Scrap Now")

        row3_layout.addWidget(self.url_input, stretch=2)
        row3_layout.addWidget(self.btn_add_url)
        row3_layout.addWidget(self.btn_scrap)

        row3_layout.addStretch()

        self.logo1 = self.create_placeholder_logo("FB", 32, 32, Qt.blue)
        self.logo2 = self.create_placeholder_logo("YT", 32, 32, Qt.red)
        row3_layout.addWidget(self.logo1)
        row3_layout.addWidget(self.logo2)

        layout.addLayout(row3_layout)

        # --- Row 4: Tables ---
        row4_layout = QHBoxLayout()
        
        # Left Table Container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.url_queue_label = QLabel("URL Queue")
        self.url_queue_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(self.url_queue_label)

        # Left Table: URL Table
        self.url_table = QTableWidget()
        self.url_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.url_table.customContextMenuRequested.connect(self.show_url_table_context_menu)
        self.url_table.setColumnCount(2)
        self.url_table.setHorizontalHeaderLabels(["ID", "URL"])
        self.url_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.url_table.setRowCount(1)
        self.url_table.setItem(0, 0, QTableWidgetItem("1"))
        self.url_table.setItem(0, 1, QTableWidgetItem("https://www.netshort.com/full-episodes/the-heiress-returns"))
        left_layout.addWidget(self.url_table)

        # Right Table Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.activity_label = QLabel("Activity Table")
        self.activity_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.activity_label)

        # Right Table: Download Activity
        self.dl_table = QTableWidget()
        self.dl_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dl_table.customContextMenuRequested.connect(self.show_dl_table_context_menu)
        self.dl_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dl_table.setColumnCount(7)
        self.dl_table.setHorizontalHeaderLabels(["ID", "Title", "URL", "Status", "Type", "Platform", "Size"])
        self.dl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.dl_table.setRowCount(1)
        self.dl_table.setItem(0, 0, QTableWidgetItem("101"))
        self.dl_table.setItem(0, 1, QTableWidgetItem("My Video"))
        self.dl_table.setItem(0, 2, QTableWidgetItem(".../video.mp4"))
        self.dl_table.setItem(0, 3, QTableWidgetItem("Downloading"))
        self.dl_table.setItem(0, 4, QTableWidgetItem("Video"))
        self.dl_table.setItem(0, 5, QTableWidgetItem("YouTube"))
        self.dl_table.setItem(0, 6, QTableWidgetItem("45 MB"))
        right_layout.addWidget(self.dl_table)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        row4_layout.addWidget(splitter)
        layout.addLayout(row4_layout, stretch=1)

        # --- Row 5: Options ---
        row5_group = QGroupBox("Configuration")
        row5_layout = QVBoxLayout()

        # 1. Download Paths
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Video Path:"))
        self.video_path_input = QLineEdit("C:/Downloads/Videos")
        path_layout.addWidget(self.video_path_input)
        path_layout.addWidget(QLabel("Photo Path:"))
        path_layout.addWidget(QLineEdit("C:/Downloads/Photos"))
        row5_layout.addLayout(path_layout)

        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Concurrent Downloads:"))
        opt_layout.addWidget(QLineEdit("3"))
        opt_layout.addWidget(QLabel("Speed Limit:"))
        opt_layout.addWidget(QLineEdit("Unlimited"))
        opt_layout.addStretch()
        row5_layout.addLayout(opt_layout)

        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("Auto-Shutdown:"))
        sys_layout.addWidget(QLineEdit("Off"))
        sys_layout.addStretch()
        row5_layout.addLayout(sys_layout)

        row5_group.setLayout(row5_layout)
        layout.addWidget(row5_group)

        # --- Row 6: Status Bar ---
        row6_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        row6_layout.addWidget(self.status_label)
        
        row6_layout.addStretch()
        
        self.btn_download_all = QPushButton("Download All")
        self.btn_download_all.clicked.connect(self.download_all_items)
        self.btn_cancel = QPushButton("Cancel")
        
        row6_layout.addWidget(self.btn_download_all)
        row6_layout.addWidget(self.btn_cancel)

        layout.addLayout(row6_layout)

    def setup_settings_ui(self):
        layout = QVBoxLayout(self.settings_tab)
        label = QLabel("Settings will be implemented here.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def show_url_table_context_menu(self, position):
        menu = QMenu()
        scrap_action = QAction("Scrap", self)
        scrap_action.triggered.connect(self.scrap_selected_url)
        menu.addAction(scrap_action)
        
        menu.addSeparator()
        
        paste_action = QAction("Paste URL", self)
        paste_action.triggered.connect(self.paste_url_from_clipboard)
        menu.addAction(paste_action)
        
        paste_all_action = QAction("Paste All URLs", self)
        paste_all_action.triggered.connect(self.paste_all_urls_from_clipboard)
        menu.addAction(paste_all_action)
        
        menu.exec_(self.url_table.viewport().mapToGlobal(position))

    def paste_url_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            # Take the first line if multiple
            url = text.split('\n')[0].strip()
            self.process_pasted_urls([url])

    def paste_all_urls_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            urls = [line.strip() for line in text.split('\n') if line.strip()]
            self.process_pasted_urls(urls)

    def process_pasted_urls(self, urls):
        invalid_urls = []
        added_count = 0
        
        for url in urls:
            platform = self.platform_manager.get_platform_for_url(url)
            if platform:
                self.add_url_to_table(url)
                added_count += 1
            else:
                invalid_urls.append(url)
        
        if invalid_urls:
            msg = "The following URLs are not supported:\n\n"
            msg += "\n".join(invalid_urls[:10])
            if len(invalid_urls) > 10:
                msg += f"\n...and {len(invalid_urls) - 10} more."
            QMessageBox.warning(self, "Unsupported URLs", msg)
            
        if added_count > 0:
            self.status_label.setText(f"Added {added_count} URLs to queue.")

    def add_url_to_table(self, url):
        # Check if already exists to avoid duplicates (optional but good UX)
        for row in range(self.url_table.rowCount()):
            item = self.url_table.item(row, 1)
            if item and item.text() == url:
                return

        row = self.url_table.rowCount()
        self.url_table.insertRow(row)
        self.url_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.url_table.setItem(row, 1, QTableWidgetItem(url))

    def show_dl_table_context_menu(self, position):
        menu = QMenu()
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.select_all_dl_items)
        menu.addAction(select_all_action)
        
        download_action = QAction("Download Selected", self)
        download_action.triggered.connect(self.download_selected_items)
        menu.addAction(download_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected_items)
        menu.addAction(delete_action)
        
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_selected_folder)
        menu.addAction(open_folder_action)
        
        menu.exec_(self.dl_table.viewport().mapToGlobal(position))

    def select_all_dl_items(self):
        self.dl_table.selectAll()
        
    def delete_selected_items(self):
        # Iterate in reverse order to avoid index shifting issues when removing
        rows_to_remove = sorted([item.row() for item in self.dl_table.selectedItems()], reverse=True)
        # Use set to process each row only once (since multiple items can be selected in same row)
        unique_rows = []
        seen = set()
        for r in rows_to_remove:
            if r not in seen:
                unique_rows.append(r)
                seen.add(r)
        
        for row in unique_rows:
            # Cancel active download if any
            if row in self.active_downloads:
                self.active_downloads[row].cancel()
                del self.active_downloads[row]
            
            # Remove from table
            self.dl_table.removeRow(row)

    def open_selected_folder(self):
        # Determine path (from input for now, ideally per-item if stored)
        path = self.video_path_input.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.status_label.setText(f"Folder does not exist: {path}")

    def download_all_items(self):
        all_rows = set(range(self.dl_table.rowCount()))
        self.start_download_for_rows(all_rows)

    def download_selected_items(self):
        selected_rows = set()
        for item in self.dl_table.selectedItems():
            selected_rows.add(item.row())
            
        if not selected_rows:
            self.status_label.setText("No items selected for download.")
            return

        self.start_download_for_rows(selected_rows)

    def start_download_for_rows(self, rows):
        self.status_label.setText(f"Starting download for {len(rows)} items...")
        
        download_path = self.video_path_input.text()
        
        for row in rows:
            if row in self.active_downloads:
                continue # Already downloading
                
            # Get data from table
            title_item = self.dl_table.item(row, 1)
            url_item = self.dl_table.item(row, 2)
            platform_item = self.dl_table.item(row, 5)
            
            # Safety check if items are valid
            if not title_item or not url_item:
                continue

            title = title_item.text()
            url = url_item.text()
            platform = platform_item.text() if platform_item else "Unknown"
            
            video_data = {
                "title": title,
                "url": url,
                "platform": platform
            }
            
            # Update Status
            self.dl_table.setItem(row, 3, QTableWidgetItem("Starting..."))
            
            # Create Worker
            worker = DownloadWorker(row, video_data, download_path)
            worker.progress.connect(self.on_download_progress)
            worker.finished.connect(self.on_download_finished)
            worker.error.connect(self.on_download_error)
            
            self.active_downloads[row] = worker
            worker.start()

    def on_download_progress(self, row, percent, speed):
        self.dl_table.setItem(row, 3, QTableWidgetItem(f"Downloading {percent}%"))
        
    def on_download_finished(self, row, status):
        self.dl_table.setItem(row, 3, QTableWidgetItem(status))
        if row in self.active_downloads:
            del self.active_downloads[row]
            
    def on_download_error(self, row, error_msg):
        self.dl_table.setItem(row, 3, QTableWidgetItem("Error"))
        # Optional: Show error in tooltip or log
        self.status_label.setText(f"Error on row {row}: {error_msg}")
        if row in self.active_downloads:
            del self.active_downloads[row]

    def scrap_selected_url(self):
        current_row = self.url_table.currentRow()
        if current_row < 0:
            return
            
        url_item = self.url_table.item(current_row, 1)
        if not url_item:
            return
            
        url = url_item.text()
        self.status_label.setText(f"Checking for platform: {url}...")
        QApplication.processEvents()
        
        platform = self.platform_manager.get_platform_for_url(url)
        if not platform:
            self.status_label.setText(f"No platform found for this URL.")
            return

        try:
            # Pass a lambda to update the status label from the plugin
            videos = platform.scrap(url, status_callback=lambda msg: self.update_status(msg))
            self.add_videos_to_dl_table(videos)
            self.status_label.setText(f"Scraping complete. Found {len(videos)} videos.")
        except Exception as e:
            self.status_label.setText(f"Error scraping: {str(e)}")

    def update_status(self, message):
        self.status_label.setText(message)
        QApplication.processEvents()

    def add_videos_to_dl_table(self, videos):
        start_row = self.dl_table.rowCount()
        self.dl_table.setRowCount(start_row + len(videos))
        
        for i, video in enumerate(videos):
            row = start_row + i
            self.dl_table.setItem(row, 0, QTableWidgetItem(str(1000 + row)))
            self.dl_table.setItem(row, 1, QTableWidgetItem(video['title']))
            self.dl_table.setItem(row, 2, QTableWidgetItem(video['url']))
            self.dl_table.setItem(row, 3, QTableWidgetItem("Queued"))
            self.dl_table.setItem(row, 4, QTableWidgetItem("Video"))
            self.dl_table.setItem(row, 5, QTableWidgetItem(video['platform']))
            self.dl_table.setItem(row, 6, QTableWidgetItem("Unknown"))

    def create_placeholder_logo(self, text, w, h, color):
        label = QLabel()
        pixmap = QPixmap(w, h)
        pixmap.fill(color)
        label.setPixmap(pixmap)
        label.setToolTip(text)
        return label

    def update_timer(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.timer_label.setText(current_time)
