from __future__ import annotations

from cachetools import TTLCache

# Cache popular search queries (both posts and users)
# Very simple in-memory cache; good enough for homework.
posts_search_cache: TTLCache[str, list[int]] = TTLCache(maxsize=512, ttl=60)
users_search_cache: TTLCache[str, list[int]] = TTLCache(maxsize=512, ttl=60)
