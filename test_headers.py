import urllib.request
import urllib.error
import http.cookiejar

# The problematic URL
url = "https://hwzthls.dramaboxdb.com/33/9x1/91x6/916x4/91640000024/700296233_1/m3u8/700296233.720p.m3u8"

# The page where the video is located
page_url = "https://www.dramaboxdb.com/ep/42000004619_between-lies-and-love-dubbed/700296233_Episode-1"

# Setup Cookie Jar
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

base_headers = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
]
opener.addheaders = base_headers

print("1. Fetching Main Page to get Cookies...")
try:
    req = urllib.request.Request(page_url)
    with opener.open(req) as response:
        print(f"Page Fetch Status: {response.status}")
        print("Cookies captured:")
        for cookie in cookie_jar:
            print(f" - {cookie.name}: {cookie.value}")
except Exception as e:
    print(f"Page Fetch Error: {e}")

print("\n2. Testing m3u8 with Cookies & Referer...")
# Manually add Referer for this specific request
req = urllib.request.Request(url)
req.add_header('Referer', page_url)
# Cookies are added automatically by the opener

try:
    with opener.open(req) as response:
        print(f"m3u8 Fetch Status: {response.status}")
        print("Success!")
except urllib.error.HTTPError as e:
    print(f"Failed: {e.code} {e.reason}")
except Exception as e:
    print(f"Error: {e}")