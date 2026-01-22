from platforms.netshort import NetShortPlatform

class PlatformManager:
    def __init__(self):
        self.platforms = []
        self.register_platforms()

    def register_platforms(self):
        # Register all available platforms here
        self.platforms.append(NetShortPlatform())

    def get_platform_for_url(self, url):
        for platform in self.platforms:
            if platform.can_handle(url):
                return platform
        return None
