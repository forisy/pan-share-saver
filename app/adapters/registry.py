from typing import Optional
import re
from urllib.parse import urlparse
from ..base import ShareAdapter
from .baidu import BaiduAdapter
from .alipan import AlipanAdapter
from .juejin import JuejinAdapter
from .v2ex import V2exAdapter
from .ptfans import PtfansAdapter
from ..logger import create_logger

_REGISTRY = {
    "baidu": BaiduAdapter(),
    "baidupan": BaiduAdapter(),
    "alipan": AlipanAdapter(),
    "aliyundrive": AlipanAdapter(),
    "juejin": JuejinAdapter(),
    "v2ex": V2exAdapter(),
    "ptfans": PtfansAdapter(),
}

logger = create_logger("adapter-registry")

def _extract_url(link: str) -> Optional[str]:
    m = re.search(r'https?://[^\s]+', link)
    return m.group(0) if m else None

def resolve_adapter_from_link(link: str) -> Optional[ShareAdapter]:
    url = _extract_url(link) or link
    try:
        netloc = urlparse(url).netloc.lower()
        logger.debug(f"Resolving adapter for link: {link}, netloc: {netloc}")
    except Exception as e:
        logger.error(f"Failed to parse URL: {link}, error: {e}")
        return None
    if netloc.endswith('pan.baidu.com'):
        logger.info(f"Resolved Baidu adapter for link: {link}")
        return _REGISTRY.get('baidu')
    if netloc.endswith('aliyundrive.com') or netloc.endswith('alipan.com'):
        logger.info(f"Resolved Alipan adapter for link: {link}")
        return _REGISTRY.get('alipan')
    logger.warning(f"No adapter found for link: {link}, netloc: {netloc}")
    return None

def resolve_adapter_from_provider(provider: str) -> Optional[ShareAdapter]:
    logger.info(f"Resolving adapter for provider: {provider}")
    adapter = _REGISTRY.get(provider.lower())
    if adapter is None:
        logger.warning(f"No adapter found for provider: {provider}")
    else:
        logger.info(f"Adapter found for provider: {provider}")
    return adapter