import re
import urllib.request
import urllib.error
from urllib.parse import urljoin
from .base import BasePlatform

class NetShortPlatform(BasePlatform):
    def can_handle(self, url):
        return "netshort.com" in url

    def scrap(self, start_url, status_callback=None):
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
            # Update status via callback if provided
            if status_callback:
                status_callback(f"Scraping Page {page_num}...")
            
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
                    "platform": "NetShort"
                })
            
            # If no *new* videos found on this page, assume we reached the end or a duplicate page
            if not videos_on_page:
                break
                
            all_videos.extend(videos_on_page)
            
            # Prepare next page
            page_num += 1
            current_url = f"{base_url}/page/{page_num}"
            
        return all_videos

    def resolve_video_url(self, episode_url):
        # In a real scenario, this would request the episode_url, 
        # find the <video> tag or m3u8 link, and return that.
        # For this prototype, we'll try to find a video source or just return the page url
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(episode_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            # Naive regex for mp4/m3u8
            # This is highly dependent on the site structure
            video_match = re.search(r'src=["\']([^"\']+\.(?:mp4|m3u8))["\']', html)
            if video_match:
                return video_match.group(1)
        except:
            pass
            
        return None # Failed to resolve
