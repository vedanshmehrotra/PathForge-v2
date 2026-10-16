"""Validate stored problem links without guessing from database IDs or titles."""

import re
from urllib.parse import urlsplit


def problem_url(value):
    if not isinstance(value, str) or re.search(r"[\x00-\x20\\]", value):
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or url.hostname not in {"leetcode.com", "www.leetcode.com"}
                or url.username is not None or url.password is not None or url.port is not None
                or url.query or url.fragment):
            return None
    except ValueError:
        return None
    if not re.fullmatch(r"/problems/[a-z0-9]+(?:-[a-z0-9]+)*/?", url.path):
        return None
    return f"https://leetcode.com{url.path.rstrip('/')}/"
