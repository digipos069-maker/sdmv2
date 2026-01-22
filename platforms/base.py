from abc import ABC, abstractmethod

class BasePlatform(ABC):
    @abstractmethod
    def can_handle(self, url):
        """Returns True if this platform can handle the URL."""
        pass

    @abstractmethod
    def scrap(self, url, status_callback=None):
        """
        Scraps the URL for videos. 
        Returns a list of dicts with keys: 'title', 'url', 'platform'.
        status_callback is a function that accepts a string for status updates.
        """
        pass

    @abstractmethod
    def resolve_video_url(self, episode_url):
        """
        Resolves the actual video file URL from the episode page URL.
        Returns the video URL string or None if failed.
        """
        pass
