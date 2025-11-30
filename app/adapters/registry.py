from typing import Optional
import re
from urllib.parse import urlparse
from .base import ShareAdapter
from .baidu import BaiduAdapter

_REGISTRY = {
    "baidu": BaiduAdapter(),
    "baidupan": BaiduAdapter(),
}

def _extract_url(link: str) -> Optional[str]:
    m = re.search(r'https?://[^\s]+', link)
    return m.group(0) if m else None

def resolve_adapter_from_link(link: str) -> Optional[ShareAdapter]:
    url = _extract_url(link) or link
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return None
    if netloc.endswith('pan.baidu.com'):
        return _REGISTRY.get('baidu')
    return None

def resolve_adapter_from_provider(provider: str) -> Optional[ShareAdapter]:
    return _REGISTRY.get(provider.lower())