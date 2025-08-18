from __future__ import annotations
from typing import Literal, Any, Optional, cast, TYPE_CHECKING
import primp
from loguru import logger

if TYPE_CHECKING:
    # Type alias for impersonate values for type checking
    ImpersonateType = Literal[
        # Chrome
        "chrome_100", "chrome_101", "chrome_104", "chrome_105", "chrome_106", 
        "chrome_107", "chrome_108", "chrome_109", "chrome_114", "chrome_116", 
        "chrome_117", "chrome_118", "chrome_119", "chrome_120", "chrome_123", 
        "chrome_124", "chrome_126", "chrome_127", "chrome_128", "chrome_129", 
        "chrome_130", "chrome_131", "chrome_133",
        # Edge
        "edge_101", "edge_122", "edge_127", "edge_131",
        # Safari
        "safari_ios_17.2", "safari_ios_17.4.1", "safari_ios_16.5", "safari_ios_18.1.1",
        "safari_15.3", "safari_15.5", "safari_15.6.1", "safari_16", "safari_16.5", 
        "safari_17.0", "safari_17.2.1", "safari_17.4.1", "safari_17.5", "safari_18", 
        "safari_18.2", "safari_ipad_18",
        # OkHttp
        "okhttp_3.9", "okhttp_3.11", "okhttp_3.13", "okhttp_3.14", "okhttp_4.9", 
        "okhttp_4.10", "okhttp_5",
        # Firefox
        "firefox_109", "firefox_117", "firefox_128", "firefox_133", "firefox_135",
        # Random
        "random"
    ]
else:
    ImpersonateType = str

class _BaseClient:
    def __init__(self, golden_key: str, user_agent: str | None = None,
                 requests_timeout: int | float = 10, proxy: str | None = None,
                 locale: Literal["ru", "en", "uk"] | None = None, impersonate: ImpersonateType | None = "chrome_124"):
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
            locale = cast(Literal["ru", "en", "uk"] | None, self.locale)
        if locale in locales:
            return url.replace(f"https://funpay.com/", f"https://funpay.com/{locale}/", 1)
        return url

class SyncClient(_BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cast to Any to avoid type conflict with primp's internal IMPERSONATE type
        self._client = primp.Client(impersonate=cast(Any, self.impersonate), proxy=self.proxy, timeout=self.requests_timeout)

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
        # Cast to Any to avoid type conflict with primp's internal IMPERSONATE type
        self._client = primp.AsyncClient(impersonate=cast(Any, self.impersonate), proxy=self.proxy, timeout=self.requests_timeout)

    async def get(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return await self._client.get(url, headers=headers, **kwargs)

    async def post(self, url: str, **kwargs):
        url = self._normalize_url(url)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        return await self._client.post(url, headers=headers, **kwargs)
