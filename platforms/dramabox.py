import re
import urllib.request
import urllib.error
import os
from urllib.parse import urljoin
from .base import BasePlatform

class DramaboxPlatform(BasePlatform):
    def can_handle(self, url):
        return "dramaboxdb.com" in url

    def scrap(self, start_url, status_callback=None):
        all_videos = []
        
        if status_callback:
            status_callback(f"Scraping Dramabox: {start_url}...")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(start_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            # 1. Add current video
            current_title = "Unknown Episode"
            title_match = re.search(r'<title>(.*?)</title>', html)
            if title_match:
                current_title = title_match.group(1).split('|')[0].strip()
                
            all_videos.append({
                "title": current_title,
                "url": start_url,
                "platform": "Dramabox"
            })
            
            # 2. Find other episodes
            # The user mentioned "RightList_tabTitle__zvZRp" but typical extraction relies on hrefs.
            # Looking for links like /ep/ID_title/ID_Episode-N
            # We'll look for the specific pattern observed in the URL provided.
            
            # Extract base ID
            base_match = re.search(r'/ep/(\d+_[^/]+)/', start_url)
            if base_match:
                base_path = base_match.group(1)
                # Find all links containing this base path
                # Pattern: href="/ep/{base_path}/(\d+_Episode-\d+)"
                pattern = r'href=["\']/ep/' + re.escape(base_path) + r'/([^"\']+)["\']'
                matches = re.findall(pattern, html)
                
                seen_ids = set()
                # Add current one to seen
                current_ep_id = start_url.split('/')[-1]
                seen_ids.add(current_ep_id)
                
                for match in matches:
                    if match not in seen_ids:
                        seen_ids.add(match)
                        full_url = f"https://www.dramaboxdb.com/ep/{base_path}/{match}"
                        
                        # Generate a title
                        # match looks like "700296233_Episode-1"
                        parts = match.split('_')
                        ep_title = parts[-1].replace('-', ' ') if len(parts) > 1 else match
                        
                        all_videos.append({
                            "title": f"Episode {ep_title}",
                            "url": full_url,
                            "platform": "Dramabox"
                        })
            
            if status_callback:
                status_callback(f"Found {len(all_videos)} episodes.")
                
        except Exception as e:
            print(f"Error scraping Dramabox: {e}")
            if status_callback:
                status_callback(f"Error: {e}")
            
        return all_videos

    def resolve_video_url(self, episode_url):
        print(f"[DEBUG] Resolving Dramabox URL: {episode_url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(episode_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
            
            # Search for m3u8
            # Look for common patterns: .m3u8 inside quotes
            # Handle escaped slashes if JSON
            video_match = re.search(r'(https?(?::|%3A)(?:/|%2F|\\/){2}[^"\'\s<>]+?\.m3u8)', html, re.IGNORECASE)
            
            if video_match:
                found_url = video_match.group(1)
                found_url = found_url.replace(r'\\/', '/')
                found_url = found_url.replace('%3A', ':').replace('%2F', '/')
                print(f"[DEBUG] Found m3u8 URL: {found_url}")
                return found_url
                
            # If no m3u8, look for mp4
            video_match_mp4 = re.search(r'(https?(?::|%3A)(?:/|%2F|\\/){2}[^"\'\s<>]+?\.mp4)', html, re.IGNORECASE)
            if video_match_mp4:
                found_url = video_match_mp4.group(1)
                found_url = found_url.replace(r'\\/', '/')
                found_url = found_url.replace('%3A', ':').replace('%2F', '/')
                print(f"[DEBUG] Found mp4 URL: {found_url}")
                return found_url

            # Dump debug info if nothing found
            print("[DEBUG] No video found. Dumping HTML snippet:")
            print(html[:500])
            with open("debug_dramabox.html", "w", encoding="utf-8") as f:
                f.write(html)
                
        except Exception as e:
            print(f"[ERROR] Dramabox resolution failed: {e}")
            
        return None
