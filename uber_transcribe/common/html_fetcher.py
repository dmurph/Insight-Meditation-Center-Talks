from typing import Protocol
import requests

class HtmlFetcher(Protocol):
    """Protocol for fetching HTML content from a URL."""
    def fetch(self, url: str) -> str:
        ...

class RequestsHtmlFetcher:
    """Real implementation of HtmlFetcher using the requests library."""
    def fetch(self, url: str) -> str:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return ""

class FakeHtmlFetcher:
    """Fake implementation of HtmlFetcher for tests."""
    def __init__(self, pages: dict[str, str]):
        self._pages = pages

    def fetch(self, url: str) -> str:
        return self._pages.get(url, "")