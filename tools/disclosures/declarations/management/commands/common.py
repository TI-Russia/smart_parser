import re
from deduplicate.config import resolve_fullname

def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


