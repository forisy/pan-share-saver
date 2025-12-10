from typing import Optional
import re
from urllib.parse import urlparse
from ..base import ShareAdapter
from .baidu import BaiduAdapter
from .aliyun import AliyunAdapter
from .juejin import JuejinAdapter

_REGISTRY = {
    "baidu": BaiduAdapter(),
    "baidupan": BaiduAdapter(),
    "aliyun": AliyunAdapter(),
    "aliyundrive": AliyunAdapter(),
    "alipan": AliyunAdapter(),
    "juejin": JuejinAdapter(),
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
    if netloc.endswith('aliyundrive.com') or netloc.endswith('alipan.com'):
        return _REGISTRY.get('aliyun')
    return None

def resolve_adapter_from_provider(provider: str) -> Optional[ShareAdapter]:
    return _REGISTRY.get(provider.lower())
