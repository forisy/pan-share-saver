import json
from typing import Dict, List, Union, Optional, Any
from ..logger import create_logger

logger = create_logger("cookies")

def parse_cookie_string(cookie_input: Optional[Any]) -> List[Dict[str, str]]:
    """
    Parse cookie input which can be a string, dict, or list and convert it to a list of cookie dictionaries
    that can be used by Playwright.
    
    Args:
        cookie_input: Cookie data as string, dict, or list
        
    Returns:
        List of cookie dictionaries in Playwright format
    """
    if not cookie_input:
        return []
    
    cookies = []
    
    if isinstance(cookie_input, str):
        # Try parsing as JSON first (for JSON cookie format)
        if cookie_input.strip().startswith(('{', '[')):
            try:
                parsed_cookies = json.loads(cookie_input)
                if isinstance(parsed_cookies, list):
                    # Already in the format expected by Playwright
                    cookies = parsed_cookies
                elif isinstance(parsed_cookies, dict):
                    # Convert dict to Playwright format
                    for domain, domain_cookies in parsed_cookies.items():
                        if isinstance(domain_cookies, dict):
                            for name, value in domain_cookies.items():
                                cookie_entry = {
                                    "name": name,
                                    "value": str(value),
                                    "domain": domain.lstrip('.'),
                                    "path": "/"
                                }
                                if domain.startswith('.'):
                                    cookie_entry["domain"] = domain
                                cookies.append(cookie_entry)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse cookie string as JSON: {cookie_input[:100]}...")
        # If JSON parsing didn't work, try parsing as semicolon-separated string
        elif '=' in cookie_input and (';' in cookie_input or ',' in cookie_input):
            # Parse "key1=value1; key2=value2" format
            cookie_pairs = [pair.strip() for pair in cookie_input.replace(',', ';').split(';') if pair.strip()]
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.split('=', 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": "",  # Will be set automatically when navigating
                        "path": "/"
                    })
        # If the format doesn't match common formats, treat as raw string
        elif cookie_input.strip():
            logger.warning(f"Unrecognized cookie format: {cookie_input[:100]}...")
            
    elif isinstance(cookie_input, dict):
        # Handle dictionary format directly
        for domain, domain_cookies in cookie_input.items():
            if isinstance(domain_cookies, dict):
                for name, value in domain_cookies.items():
                    cookie_entry = {
                        "name": name,
                        "value": str(value),
                        "domain": domain.lstrip('.'),
                        "path": "/"
                    }
                    if domain.startswith('.'):
                        cookie_entry["domain"] = domain
                    cookies.append(cookie_entry)
    elif isinstance(cookie_input, list):
        # Already in the format expected by Playwright
        cookies = cookie_input
    else:
        logger.warning(f"Unrecognized cookie input type: {type(cookie_input)}")
        
    if cookies:
        logger.info(f"Parsed {len(cookies)} cookies from input")
    else:
        logger.warning("No cookies could be parsed from the provided cookie input")
        
    return cookies