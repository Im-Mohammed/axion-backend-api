"""
rate_limiter.py
Simple in-memory sliding-window rate limiter.
Thread-safe via a Lock. Suitable for single-process shared-hosting deployments.
"""

import time
from threading import Lock
from collections import defaultdict


class RateLimiter:
    """
    Allows max_requests per window_seconds per IP address.
    Old entries are pruned on each check to keep memory bounded.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests     = max_requests
        self.window_seconds   = window_seconds
        self._requests: dict  = defaultdict(list)
        self._lock            = Lock()

    def is_allowed(self, identifier: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune entries outside the window
            self._requests[identifier] = [
                t for t in self._requests[identifier] if t > cutoff
            ]
            if len(self._requests[identifier]) >= self.max_requests:
                return False
            self._requests[identifier].append(now)
            return True

    def reset(self, identifier: str):
        with self._lock:
            self._requests.pop(identifier, None)