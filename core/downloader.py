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
            print(f"[DEBUG] Downloading from: {real_url}")
            
            if ".m3u8" in real_url:
                self.download_m3u8(real_url, filepath)
            else:
                self.download_file(real_url, filepath)

        except Exception as e:
            print(f"[ERROR] Download failed: {str(e)}")
            self.error.emit(self.row_id, str(e))

    def download_m3u8(self, url, filepath):
        try:
            # Simple native HLS downloader
            # 1. Fetch playlist
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                playlist = response.read().decode('utf-8')
            
            # 2. Parse segments
            base_url = url.rsplit('/', 1)[0]
            lines = playlist.splitlines()
            segments = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        segments.append(line)
                    else:
                        segments.append(f"{base_url}/{line}")
            
            if not segments:
                # Might be a master playlist, try finding the highest quality stream
                for line in lines:
                    if ".m3u8" in line:
                        if line.startswith('http'):
                            new_url = line
                        else:
                            new_url = f"{base_url}/{line}"
                        print(f"[DEBUG] Found master playlist, redirecting to: {new_url}")
                        self.download_m3u8(new_url, filepath)
                        return

                raise Exception("No segments found in m3u8 playlist")

            # 3. Download segments
            total_segments = len(segments)
            temp_file = filepath + ".ts"
            
            with open(temp_file, 'wb') as outfile:
                for i, segment_url in enumerate(segments):
                    if self.is_cancelled:
                        outfile.close()
                        os.remove(temp_file)
                        self.finished.emit(self.row_id, "Cancelled")
                        return

                    # Retry logic for segments
                    for attempt in range(3):
                        try:
                            seg_req = urllib.request.Request(segment_url, headers=headers)
                            with urllib.request.urlopen(seg_req, timeout=10) as seg_resp:
                                outfile.write(seg_resp.read())
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"[WARN] Failed to download segment {i}: {e}")
                    
                    # Progress
                    percent = int(((i + 1) / total_segments) * 100)
                    self.progress.emit(self.row_id, percent, 0)
            
            # Rename .ts to target (simple concat, might not play everywhere without ffmpeg remux)
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_file, filepath)
            
            self.finished.emit(self.row_id, "Completed")

        except Exception as e:
            raise e

    def download_file(self, url, filepath):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                content_type = response.getheader('Content-Type')
                print(f"[DEBUG] Content-Type: {content_type}")
                
                if content_type and 'text/html' in content_type:
                    raise Exception("Download failed: URL returned an HTML page instead of video. The video might be protected, require login, or the URL is invalid.")

                content_length = response.getheader('Content-Length')
                total_size = int(content_length.strip()) if content_length else 0
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
