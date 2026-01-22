import os
import requests
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
        self.session = requests.Session()

    def load_cookies(self, domain):
        cookie_file = os.path.join("config", f"{domain}_cookies.txt")
        if not os.path.exists(cookie_file):
            return
            
        try:
            cookie_parts = []
            with open(cookie_file, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        # domain, flag, path, secure, expiration, name, value
                        # Load into session for general use
                        self.session.cookies.set(parts[5], parts[6], domain=parts[0])
                        # Also build a raw cookie string for forced headers
                        cookie_parts.append(f"{parts[5]}={parts[6]}")
            
            if cookie_parts:
                forced_cookie_str = "; ".join(cookie_parts)
                print(f"[DEBUG] Loaded {len(cookie_parts)} cookies for {domain}")
                # Force cookie header for this domain's requests
                # This overrides the jar logic if the jar fails to match subdomains
                self.session.headers['Cookie'] = forced_cookie_str
                
        except Exception as e:
            print(f"[WARN] Failed to load cookies: {e}")

    def run(self):
        try:
            url = self.video_data['url']
            title = self.video_data['title']
            platform_name = self.video_data['platform']

            # Configure Session Headers with Full Browser Mimicry
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site', # Usually cross-site for CDNs
                'Origin': 'https://www.dramaboxdb.com',
                'Referer': 'https://www.dramaboxdb.com/'
            })

            # Load Cookies
            if "dramaboxdb.com" in url:
                self.load_cookies("www.dramaboxdb.com")
                # Specific fix: Ensure Referer matches the page exactly if provided, 
                # but for m3u8 on CDN, origin is often more important.
                # However, your logs showed 403. 
                # Let's trust the PlatformManager resolved URL logic, but force the Origin.


            # 1. Resolve true video URL
            platform = self.platform_manager.get_platform_for_url(url)
            if platform:
                # Pass session to resolver if supported? 
                # For now, let the platform do its own thing or we might need to refactor platform to accept session
                # But platform uses urllib currently.
                real_url = platform.resolve_video_url(url)
                if not real_url:
                    self.error.emit(self.row_id, "Failed to resolve video URL")
                    return
            else:
                real_url = url 

            # 2. Setup path
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            filename = f"{safe_title}.mp4" 
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
            # 1. Fetch playlist
            response = self.session.get(url)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch m3u8: HTTP {response.status_code}")
                
            playlist = response.text
            base_url = url.rsplit('/', 1)[0]
            lines = playlist.splitlines()
            
            # Check if Master Playlist
            if "#EXT-X-STREAM-INF" in playlist:
                # Find best quality
                best_bandwidth = -1
                best_url = None
                
                for i, line in enumerate(lines):
                    if line.startswith("#EXT-X-STREAM-INF"):
                        # Extract bandwidth if possible
                        bw = 0
                        if "BANDWIDTH=" in line:
                            try:
                                bw_part = line.split("BANDWIDTH=")[1].split(",")[0]
                                bw = int(bw_part)
                            except:
                                pass
                        
                        # Get URL from next line
                        if i + 1 < len(lines):
                            stream_url = lines[i+1].strip()
                            if stream_url and not stream_url.startswith("#"):
                                if not stream_url.startswith("http"):
                                    stream_url = f"{base_url}/{stream_url}"
                                
                                if bw > best_bandwidth:
                                    best_bandwidth = bw
                                    best_url = stream_url
                
                if best_url:
                    print(f"[DEBUG] Selected best stream: {best_url}")
                    # Recursion is safe here because we are moving from Master -> Media
                    self.download_m3u8(best_url, filepath)
                    return
            
            # 2. Parse Media Segments
            segments = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        segments.append(line)
                    else:
                        segments.append(f"{base_url}/{line}")
            
            if not segments:
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

                    # Retry logic
                    for attempt in range(3):
                        try:
                            # Stream=True to avoid loading whole segment in memory if large
                            with self.session.get(segment_url, stream=True, timeout=15) as r:
                                r.raise_for_status()
                                for chunk in r.iter_content(chunk_size=8192):
                                    outfile.write(chunk)
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"[WARN] Failed to download segment {i}: {e}")
                                if "403" in str(e):
                                    raise Exception("403 Forbidden on Segment - Cookies might be invalid for CDN")
                    
                    percent = int(((i + 1) / total_segments) * 100)
                    self.progress.emit(self.row_id, percent, 0)
            
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_file, filepath)
            
            self.finished.emit(self.row_id, "Completed")

        except Exception as e:
            raise e

    def download_file(self, url, filepath):
        try:
            with self.session.get(url, stream=True) as response:
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    raise Exception("Download failed: URL returned HTML. Check login/protection.")

                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            f.close()
                            os.remove(filepath)
                            self.finished.emit(self.row_id, "Cancelled")
                            return
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(self.row_id, percent, 0)
            
            self.finished.emit(self.row_id, "Completed")

        except Exception as e:
            raise e

    def cancel(self):
        self.is_cancelled = True
