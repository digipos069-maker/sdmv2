import os
import urllib.request
from PyQt5.QtCore import QThread, pyqtSignal
from core.manager import PlatformManager

class DownloadWorker(QThread):
    progress = pyqtSignal(int, int, int) # row_id, percentage, speed (kbps) - simplistic
    finished = pyqtSignal(int, str) # row_id, status message
    error = pyqtSignal(int, str) # row_id, error message

    def __init__(self, row_id, video_data, download_path):
        super().__init__()
        self.row_id = row_id
        self.video_data = video_data
        self.download_path = download_path
        self.platform_manager = PlatformManager()
        self.is_cancelled = False

    def run(self):
        try:
            url = self.video_data['url']
            title = self.video_data['title']
            platform_name = self.video_data['platform']

            # 1. Resolve true video URL
            platform = self.platform_manager.get_platform_for_url(url)
            if platform:
                real_url = platform.resolve_video_url(url)
                if not real_url:
                    self.error.emit(self.row_id, "Failed to resolve video URL")
                    return
            else:
                real_url = url # Direct download if no platform logic

            # 2. Setup path
            # Sanitize filename
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            filename = f"{safe_title}.mp4" # Assuming mp4 for now
            filepath = os.path.join(self.download_path, filename)

            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)

            # 3. Download
            self.download_file(real_url, filepath)

        except Exception as e:
            self.error.emit(self.row_id, str(e))

    def download_file(self, url, filepath):
        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.getheader('Content-Length').strip())
                downloaded = 0
                block_size = 8192
                
                with open(filepath, 'wb') as f:
                    while True:
                        if self.is_cancelled:
                            f.close()
                            os.remove(filepath)
                            self.finished.emit(self.row_id, "Cancelled")
                            return

                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        downloaded += len(buffer)
                        f.write(buffer)
                        
                        # Calculate progress
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(self.row_id, percent, 0)
            
            self.finished.emit(self.row_id, "Completed")

        except Exception as e:
            raise e

    def cancel(self):
        self.is_cancelled = True
