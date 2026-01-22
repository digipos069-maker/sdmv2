import sys
import datetime
import urllib.request
import urllib.error
import re
from urllib.parse import urljoin
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTableWidget, QTableWidgetItem, QTabWidget, 
                             QGroupBox, QFormLayout, QHeaderView, QFrame,
                             QSizePolicy, QSplitter, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor, QPalette

# --- Constants ---
# User preferred color
ACCENT_COLOR = "#032EA1"
TEXT_COLOR_ON_ACCENT = "#FFFFFF"

class DownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SDM - Downloader Manager")
        self.resize(1200, 800)
        
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
        # (Logo, Internet Speed, User Name, Timer | Checkup, License)
        row2_layout = QHBoxLayout()
        
        # Logo Placeholder
        self.logo_label = self.create_placeholder_logo("Logo", 50, 50, Qt.darkGray)
        row2_layout.addWidget(self.logo_label)

        # Info Labels
        self.ping_label = QLabel("Ping: 24ms")
        self.user_label = QLabel("User: Admin")
        self.timer_label = QLabel("00:00:00")
        
        # Timer Logic
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        row2_layout.addWidget(self.ping_label)
        row2_layout.addSpacing(20)
        row2_layout.addWidget(self.user_label)
        row2_layout.addSpacing(20)
        row2_layout.addWidget(self.timer_label)

        row2_layout.addStretch()

        # Right Side Buttons
        self.btn_checkup = QPushButton("Checkup")
        self.btn_license = QPushButton("License")
        row2_layout.addWidget(self.btn_checkup)
        row2_layout.addWidget(self.btn_license)

        layout.addLayout(row2_layout)

        # --- Row 3: Input & Actions ---
        # (Input | Add URL, Scrap Now | Logos)
        row3_layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        self.url_input.setStyleSheet("padding: 8px; border: 1px solid #CCC; border-radius: 4px;")
        
        self.btn_add_url = QPushButton("Add URL")
        self.btn_scrap = QPushButton("Scrap Now")

        row3_layout.addWidget(self.url_input, stretch=2) # Input takes more space
        row3_layout.addWidget(self.btn_add_url)
        row3_layout.addWidget(self.btn_scrap)

        row3_layout.addStretch()

        # Social Logos
        self.logo1 = self.create_placeholder_logo("FB", 32, 32, Qt.blue)
        self.logo2 = self.create_placeholder_logo("YT", 32, 32, Qt.red)
        row3_layout.addWidget(self.logo1)
        row3_layout.addWidget(self.logo2)

        layout.addLayout(row3_layout)

        # --- Row 4: Tables ---
        # (Left: URL Table | Right: Download Activity)
        row4_layout = QHBoxLayout()
        
        # Left Table: URL Table (ID, URL)
        self.url_table = QTableWidget()
        self.url_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.url_table.customContextMenuRequested.connect(self.show_url_table_context_menu)
        self.url_table.setColumnCount(2)
        self.url_table.setHorizontalHeaderLabels(["ID", "URL"])
        self.url_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # Mock Data
        self.url_table.setRowCount(1)
        self.url_table.setItem(0, 0, QTableWidgetItem("1"))
        self.url_table.setItem(0, 1, QTableWidgetItem("https://www.netshort.com/full-episodes/the-heiress-returns"))

        # Right Table: Download Activity
        # (ID, Title, URL, Status, Type, Platform, Size)
        self.dl_table = QTableWidget()
        self.dl_table.setColumnCount(7)
        self.dl_table.setHorizontalHeaderLabels(["ID", "Title", "URL", "Status", "Type", "Platform", "Size"])
        self.dl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Distribute evenly
        # Mock Data
        self.dl_table.setRowCount(1)
        self.dl_table.setItem(0, 0, QTableWidgetItem("101"))
        self.dl_table.setItem(0, 1, QTableWidgetItem("My Video"))
        self.dl_table.setItem(0, 2, QTableWidgetItem(".../video.mp4"))
        self.dl_table.setItem(0, 3, QTableWidgetItem("Downloading"))
        self.dl_table.setItem(0, 4, QTableWidgetItem("Video"))
        self.dl_table.setItem(0, 5, QTableWidgetItem("YouTube"))
        self.dl_table.setItem(0, 6, QTableWidgetItem("45 MB"))

        # Splitter to allow resizing between tables
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.url_table)
        splitter.addWidget(self.dl_table)
        splitter.setStretchFactor(0, 1) # Left table smaller
        splitter.setStretchFactor(1, 3) # Right table larger

        row4_layout.addWidget(splitter)
        layout.addLayout(row4_layout, stretch=1) # Give this row vertical expansion room

        # --- Row 5: Options (4 sub-rows/sections) ---
        # (Download Path, Download Option, System Setting)
        row5_group = QGroupBox("Configuration")
        row5_layout = QVBoxLayout()

        # 1. Download Paths
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Video Path:"))
        path_layout.addWidget(QLineEdit("C:/Downloads/Videos"))
        path_layout.addWidget(QLabel("Photo Path:"))
        path_layout.addWidget(QLineEdit("C:/Downloads/Photos"))
        row5_layout.addLayout(path_layout)

        # 2. Download Options
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Concurrent Downloads:"))
        opt_layout.addWidget(QLineEdit("3"))
        opt_layout.addWidget(QLabel("Speed Limit:"))
        opt_layout.addWidget(QLineEdit("Unlimited"))
        opt_layout.addStretch()
        row5_layout.addLayout(opt_layout)

        # 3. System Settings
        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("Auto-Shutdown:"))
        sys_layout.addWidget(QLineEdit("Off"))
        sys_layout.addStretch()
        row5_layout.addLayout(sys_layout)

        row5_group.setLayout(row5_layout)
        layout.addWidget(row5_group)

        # --- Row 6: Status Bar ---
        # (Status Text | Download All, Cancel)
        row6_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        row6_layout.addWidget(self.status_label)
        
        row6_layout.addStretch()
        
        self.btn_download_all = QPushButton("Download All")
        self.btn_cancel = QPushButton("Cancel")
        
        # Apply specific danger color to cancel if desired, 
        # but keeping to user theme for now unless requested.
        
        row6_layout.addWidget(self.btn_download_all)
        row6_layout.addWidget(self.btn_cancel)

        layout.addLayout(row6_layout)

    def setup_settings_ui(self):
        """Placeholder for Settings Tab"""
        layout = QVBoxLayout(self.settings_tab)
        label = QLabel("Settings will be implemented here.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def show_url_table_context_menu(self, position):
        menu = QMenu()
        scrap_action = QAction("Scrap", self)
        scrap_action.triggered.connect(self.scrap_selected_url)
        menu.addAction(scrap_action)
        menu.exec_(self.url_table.viewport().mapToGlobal(position))

    def scrap_selected_url(self):
        current_row = self.url_table.currentRow()
        if current_row < 0:
            return
            
        url_item = self.url_table.item(current_row, 1)
        if not url_item:
            return
            
        url = url_item.text()
        self.status_label.setText(f"Scraping: {url}...")
        QApplication.processEvents() # Force update UI
        
        try:
            videos = self.perform_scraping(url)
            self.add_videos_to_dl_table(videos)
            self.status_label.setText(f"Scraping complete. Found {len(videos)} videos.")
        except Exception as e:
            self.status_label.setText(f"Error scraping: {str(e)}")

    def perform_scraping(self, start_url):
        all_videos = []
        seen_links = set()
        
        # Determine base URL and starting page number
        # Check if URL already has /page/N
        page_match = re.search(r'(.+)/page/(\d+)/?$', start_url)
        if page_match:
            base_url = page_match.group(1)
            page_num = int(page_match.group(2))
        else:
            base_url = start_url.rstrip('/')
            page_num = 1
            
        current_url = start_url
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        while True:
            # Update UI status (must be done carefully in main thread)
            self.status_label.setText(f"Scraping Page {page_num}...")
            QApplication.processEvents()
            
            try:
                req = urllib.request.Request(current_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    html = response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                # 404 or similar means end of pages
                print(f"Stopping at {current_url}: HTTP {e.code}")
                break
            except Exception as e:
                print(f"Error scraping {current_url}: {e}")
                break
            
            # Netshort specific logic: find episode links
            pattern = re.compile(r'href=["\'](/episode/[^"\']+)["\']')
            matches = pattern.findall(html)
            
            videos_on_page = []
            
            for match in matches:
                # Avoid duplicates across pages
                if match in seen_links:
                    continue
                seen_links.add(match)
                
                full_url = urljoin(current_url, match)
                
                title = match.split('/')[-1].replace('-', ' ').title()
                # Simple cleanup for title
                title = re.sub(r'-\d+$', '', title) # Remove trailing numbers if any
                if len(title) > 30:
                    title = title[:27] + "..."
                    
                videos_on_page.append({
                    "title": title,
                    "url": full_url,
                    "platform": "NetShort" if "netshort" in base_url else "Unknown"
                })
            
            # If no *new* videos found on this page, assume we reached the end or a duplicate page
            if not videos_on_page:
                break
                
            all_videos.extend(videos_on_page)
            
            # Prepare next page
            page_num += 1
            current_url = f"{base_url}/page/{page_num}"
            
        return all_videos

    def add_videos_to_dl_table(self, videos):
        start_row = self.dl_table.rowCount()
        self.dl_table.setRowCount(start_row + len(videos))
        
        for i, video in enumerate(videos):
            row = start_row + i
            # ["ID", "Title", "URL", "Status", "Type", "Platform", "Size"]
            self.dl_table.setItem(row, 0, QTableWidgetItem(str(1000 + row)))
            self.dl_table.setItem(row, 1, QTableWidgetItem(video['title']))
            self.dl_table.setItem(row, 2, QTableWidgetItem(video['url']))
            self.dl_table.setItem(row, 3, QTableWidgetItem("Queued"))
            self.dl_table.setItem(row, 4, QTableWidgetItem("Video"))
            self.dl_table.setItem(row, 5, QTableWidgetItem(video['platform']))
            self.dl_table.setItem(row, 6, QTableWidgetItem("Unknown"))

    def create_placeholder_logo(self, text, w, h, color):
        """Creates a simple colored QPixmap as a placeholder logo."""
        label = QLabel()
        pixmap = QPixmap(w, h)
        pixmap.fill(color)
        label.setPixmap(pixmap)
        label.setToolTip(text)
        # Optional: Add text on top? Keeping it simple for now.
        return label

    def update_timer(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.timer_label.setText(current_time)

def main():
    try:
        app = QApplication(sys.argv)
        
        # Set application-wide font if needed
        # font = app.font()
        # font.setPointSize(10)
        # app.setFont(font)

        window = DownloaderApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
