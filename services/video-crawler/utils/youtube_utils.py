import re

def is_url_like(query: str) -> bool:
    """Check if query looks like a URL (should be skipped)"""
    url_patterns = [
        r'^https?://',
        r'^www\.',
        r'^youtube\.com/',
        r'^youtu\.be/',
        r'^[a-zA-Z0-9_-]{11}$'  # YouTube video ID pattern
    ]
    # Check if any pattern matches the query
    for pattern in url_patterns:
        if re.match(pattern, query):
            return True
    return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Replace spaces with underscores first
    filename = filename.replace(' ', '_')
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    filename = filename.strip('. ')
    # Limit length to prevent issues
    if len(filename) > 200:
        filename = filename[:200]
    return filename
