from __future__ import annotations
from typing import Literal, Any, Optional
import primp
from loguru import logger

class _BaseClient:
    def __init__(self, golden_key: str, user_agent: str | None = None,
                 requests_timeout: int | float = 10, proxy: Optional[dict] = None,
                 locale: Literal["ru", "en", "uk"] | None = None, impersonate: str | None = "chrome_124"):
        self.golden_key = golden_key
        self.user_agent = user_agent
        self.requests_timeout = requests_timeout
        self.proxy = proxy
        self.locale = locale
        self.impersonate = impersonate
        self.phpsessid: str | None = None
        self.csrf_token: str | None = None

    def _prepare_headers(self, headers: dict | None = None) -> dict:
        if headers is None:
            headers = {}
        headers["cookie"] = f"golden_key={self.golden_key}; cookie_prefs=1"
        if self.phpsessid:
            headers["cookie"] += f"; PHPSESSID={self.phpsessid}"
        if self.user_agent:
            headers["user-agent"] = self.user_agent
        return headers

    def _normalize_url(self, api_method: str, locale: Literal["ru", "en", "uk"] | None = None) -> str:
        api_method = "https://funpay.com/" if api_method == "https://funpay.com" else api_method
        url = api_method if api_method.startswith("https://funpay.com/") else "https://funpay.com/" + api_method
        locales = ("en", "uk")
        for loc in locales:
            url = url.replace(f"https://funpay.com/{loc}/", "https://funpay.com/", 1)
        if not locale:
            locale = self.locale
        if locale in locales:
            return url.replace(f"https://funpay.com/", f"https://funpay.com/{locale}/", 1)
        return url

class SyncClient(_BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = primp.Client(impersonate=self.impersonate, proxy=self.proxy, timeout=self.requests_timeout)

    def get(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return self._client.get(url, headers=headers, **kwargs)

    def post(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return self._client.post(url, headers=headers, **kwargs)

class AsyncClient(_BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = primp.AsyncClient(impersonate=self.impersonate, proxy=self.proxy, timeout=self.requests_timeout)

    async def get(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return await self._client.get(url, headers=headers, **kwargs)

    async def post(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return await self._client.post(url, headers=headers, **kwargs)
