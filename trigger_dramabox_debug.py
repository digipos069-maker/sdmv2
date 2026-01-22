from platforms.dramabox import DramaboxPlatform

url = "https://www.dramaboxdb.com/ep/42000004619_between-lies-and-love-dubbed/700296233_Episode-1"
platform = DramaboxPlatform()
video_url = platform.resolve_video_url(url)
print(f"Resolved URL: {video_url}")
