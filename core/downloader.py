import os
import time
import cloudscraper
from PyQt5.QtCore import QThread, pyqtSignal
from core.manager import PlatformManager

class DownloadWorker(QThread):
    progress = pyqtSignal(int, int, int) # row_id, percentage, speed (kbps)
    finished = pyqtSignal(int, str) # row_id, status message
    error = pyqtSignal(int, str) # row_id, error message

    def __init__(self, row_id, video_data, download_path):
        super().__init__()
        self.row_id = row_id
        self.video_data = video_data
        self.download_path = download_path
        self.platform_manager = PlatformManager()
        self.is_cancelled = False
        
        # Initialize CloudScraper
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

    def load_cookies(self, domain):
        cookie_file = os.path.join("config", f"{domain}_cookies.txt")
        if not os.path.exists(cookie_file):
            return
            
        try:
            cookies = []
            with open(cookie_file, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        # domain, flag, path, secure, expiration, name, value
                        # CloudScraper/Requests cookie dict
                        self.scraper.cookies.set(parts[5], parts[6], domain=parts[0], path=parts[2])
                        cookies.append(f"{parts[5]}={parts[6]}")
            
            if cookies:
                # Also force header just in case
                self.scraper.headers.update({'Cookie': "; ".join(cookies)})
                print(f"[DEBUG] Loaded cookies for {domain}")
                
        except Exception as e:
            print(f"[WARN] Failed to load cookies: {e}")

    def run(self):
        try:
            url = self.video_data['url']
            title = self.video_data['title']
            
            # Configure Headers
            self.scraper.headers.update({
                'Referer': url,
                'Origin': 'https://www.dramaboxdb.com'
            })

            # Load Cookies
            if "dramaboxdb.com" in url:
                self.load_cookies("www.dramaboxdb.com")

            # 1. Resolve true video URL
            if "dramaboxdb.com" in url:
                print(f"[DEBUG] Fetching Dramabox page with cloudscraper: {url}")
                try:
                    r_page = self.scraper.get(url)
                    if r_page.status_code != 200:
                        raise Exception(f"Failed to load page: {r_page.status_code}")
                    
                    import re
                    html = r_page.text
                    # Updated Regex: Capture everything until the closing quote, ensuring it contains .m3u8
                    # This preserves query parameters (tokens)
                    video_match = re.search(r'(https?(?::|%3A)(?:/|%2F|\\/){2}[^"\'\s<>]+?\.m3u8[^"\'\s<>]*)', html, re.IGNORECASE)
                    
                    if video_match:
                        found_url = video_match.group(1)
                        found_url = found_url.replace(r'\\/', '/')
                        found_url = found_url.replace('%3A', ':').replace('%2F', '/')
                        real_url = found_url
                        print(f"[DEBUG] Resolved m3u8: {real_url}")
                    else:
                        print("[WARN] m3u8 not found in page, falling back...")
                        platform = self.platform_manager.get_platform_for_url(url)
                        real_url = platform.resolve_video_url(url) if platform else url
                except Exception as e:
                    print(f"[ERROR] Page fetch error: {e}")
                    raise e
            else:
                platform = self.platform_manager.get_platform_for_url(url)
                real_url = platform.resolve_video_url(url) if platform else url
                if not real_url:
                    self.error.emit(self.row_id, "Failed to resolve video URL")
                    return

            # 2. Setup path
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            filename = f"{safe_title}.mp4" 
            filepath = os.path.join(self.download_path, filename)

            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)

            # 3. Download
            print(f"[DEBUG] Downloading with cloudscraper: {real_url}")
            
            if ".m3u8" in real_url:
                self.download_m3u8(real_url, filepath)
            else:
                self.download_file(real_url, filepath)

        except Exception as e:
            print(f"[ERROR] Download failed: {str(e)}")
            self.error.emit(self.row_id, str(e))

    def download_m3u8(self, url, filepath):
        try:
            response = self.scraper.get(url)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch m3u8: HTTP {response.status_code} - {response.reason}")
                
            playlist = response.text
            base_url = url.rsplit('/', 1)[0]
            lines = playlist.splitlines()
            
            # Master Playlist Logic
            if "#EXT-X-STREAM-INF" in playlist:
                best_bandwidth = -1
                best_url = None
                for i, line in enumerate(lines):
                    if line.startswith("#EXT-X-STREAM-INF"):
                        bw = 0
                        if "BANDWIDTH=" in line:
                            try:
                                bw = int(line.split("BANDWIDTH=")[1].split(",")[0])
                            except: pass
                        if i + 1 < len(lines):
                            stream_url = lines[i+1].strip()
                            if stream_url and not stream_url.startswith("#"):
                                if not stream_url.startswith("http"):
                                    stream_url = f"{base_url}/{stream_url}"
                                if bw > best_bandwidth:
                                    best_bandwidth = bw
                                    best_url = stream_url
                if best_url:
                    self.download_m3u8(best_url, filepath)
                    return

            # Segments
            segments = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        segments.append(line)
                    else:
                        segments.append(f"{base_url}/{line}")
            
            if not segments:
                raise Exception("No segments found")

            total_segments = len(segments)
            temp_file = filepath + ".ts"
            
            with open(temp_file, 'wb') as outfile:
                start_time = time.time()
                downloaded_bytes = 0
                for i, segment_url in enumerate(segments):
                    if self.is_cancelled:
                        outfile.close(); os.remove(temp_file)
                        self.finished.emit(self.row_id, "Cancelled")
                        return

                    for attempt in range(3):
                        try:
                            r = self.scraper.get(segment_url, stream=True, timeout=15)
                            if r.status_code != 200: raise Exception(f"HTTP {r.status_code}")
                            content = r.content
                            outfile.write(content)
                            downloaded_bytes += len(content)
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"[WARN] Segment {i} failed: {e}")
                                if "403" in str(e): raise Exception("403 Forbidden")
                    
                    # Progress
                    percent = int(((i + 1) / total_segments) * 100)
                    elapsed = time.time() - start_time
                    speed = int((downloaded_bytes / 1024) / elapsed) if elapsed > 0 else 0
                    self.progress.emit(self.row_id, percent, speed)
            
            if os.path.exists(filepath): os.remove(filepath)
            os.rename(temp_file, filepath)
            self.finished.emit(self.row_id, "Completed")

        except Exception as e:
            raise e

    def download_file(self, url, filepath):
        try:
            with self.scraper.get(url, stream=True) as response:
                response.raise_for_status()
                if 'text/html' in response.headers.get('Content-Type', ''):
                    raise Exception("URL returned HTML.")
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            f.close(); os.remove(filepath)
                            self.finished.emit(self.row_id, "Cancelled")
                            return
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(self.row_id, percent, 0)
            self.finished.emit(self.row_id, "Completed")
        except Exception as e:
            raise e

    def cancel(self):
        self.is_cancelled = True
