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
