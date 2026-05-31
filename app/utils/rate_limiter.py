"""
rate_limiter.py
Simple in-memory sliding-window rate limiter.
Thread-safe via a Lock. Suitable for single-process deployments.

Usage:
    from app.utils.rate_limiter import RateLimiter

    # Create with custom limits
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    # Or use presets
    limiter = RateLimiter.for_email()    # 3 per 10 min
    limiter = RateLimiter.for_chat()     # 10 per 60 sec
    limiter = RateLimiter.for_general()  # 60 per 60 sec
"""

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Sliding-window rate limiter per identifier (IP address).
    Old entries are pruned on each check to keep memory bounded.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests   = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = defaultdict(list)
        self._lock           = Lock()

    # ── Presets ────────────────────────────────────────────────────────
    @classmethod
    def for_email(cls) -> "RateLimiter":
        """
        Strict — email triggers AI generation + Resend API call.
        3 emails per 10 minutes per IP.
        Prevents abuse of the AI email pipeline.
        """
        return cls(max_requests=3, window_seconds=300)

    @classmethod
    def for_chat(cls) -> "RateLimiter":
        """
        Strict — each chat message hits OpenRouter API.
        10 messages per 60 seconds per IP.
        Prevents chatbot credit drain.
        """
        return cls(max_requests=10, window_seconds=60)

    @classmethod
    def for_general(cls) -> "RateLimiter":
        """
        Relaxed — general API browsing.
        60 requests per 60 seconds per IP.
        """
        return cls(max_requests=50, window_seconds=60)
    @classmethod
    def for_login(cls) ->"RateLimiter":
        """
        5 request per minutes
        """
        return cls(max_requests=10,window_seconds=60)

    # ── Core logic ─────────────────────────────────────────────────────
    def is_allowed(self, identifier: str) -> bool:
        now    = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune timestamps outside the window
            self._requests[identifier] = [
                t for t in self._requests[identifier] if t > cutoff
            ]
            if len(self._requests[identifier]) >= self.max_requests:
                return False
            self._requests[identifier].append(now)
            return True

    def reset(self, identifier: str):
        """Manually clear limits for an IP — useful for testing."""
        with self._lock:
            self._requests.pop(identifier, None)