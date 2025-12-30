"""
KZBIT Automation - Timing & Monitoring Module

Handles global deadline enforcement, per-account timing,
and performance metrics.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
from contextlib import asynccontextmanager

from config import GLOBAL_TIMEOUT, ACCOUNT_TIMEOUT


@dataclass
class TimingMetrics:
    """Collected timing metrics for a single account."""
    login_ms: int = 0
    navigation_ms: int = 0
    submits_ms: list[int] = field(default_factory=list)
    total_ms: int = 0
    
    @property
    def avg_submit_ms(self) -> float:
        if not self.submits_ms:
            return 0
        return sum(self.submits_ms) / len(self.submits_ms)
    
    def __str__(self) -> str:
        return (
            f"Login: {self.login_ms}ms | "
            f"Nav: {self.navigation_ms}ms | "
            f"Submits: {len(self.submits_ms)} (avg {self.avg_submit_ms:.0f}ms) | "
            f"Total: {self.total_ms}ms"
        )


class Timer:
    """Simple context-based timer."""
    
    def __init__(self):
        self._start: float = 0
        self._end: float = 0
    
    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, *args) -> None:
        self._end = time.perf_counter()
    
    @property
    def elapsed_ms(self) -> int:
        return int((self._end - self._start) * 1000)
    
    @property
    def elapsed_seconds(self) -> float:
        return self._end - self._start


class GlobalDeadline:
    """
    Global 10-minute deadline enforcer.
    
    CRITICAL: All operations must check this before proceeding.
    """
    
    def __init__(self, timeout_seconds: int = GLOBAL_TIMEOUT):
        self._timeout = timeout_seconds
        self._start_time: Optional[float] = None
        self._cancelled = False
    
    def start(self) -> None:
        """Start the global timer."""
        self._start_time = time.perf_counter()
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the deadline (for testing)."""
        self._cancelled = True
    
    @property
    def elapsed_seconds(self) -> float:
        """Seconds elapsed since start."""
        if self._start_time is None:
            return 0
        return time.perf_counter() - self._start_time
    
    @property
    def remaining_seconds(self) -> float:
        """Seconds remaining before deadline."""
        return max(0, self._timeout - self.elapsed_seconds)
    
    @property
    def is_expired(self) -> bool:
        """Check if deadline has passed."""
        if self._cancelled:
            return False
        if self._start_time is None:
            return False
        return self.elapsed_seconds >= self._timeout
    
    def check(self) -> None:
        """Raise TimeoutError if deadline exceeded."""
        if self.is_expired:
            raise TimeoutError(
                f"Global deadline exceeded: {self.elapsed_seconds:.1f}s >= {self._timeout}s"
            )


class AccountTimer:
    """
    Per-account timing with early termination.
    
    Skips slow accounts to preserve time for others.
    """
    
    def __init__(
        self,
        email: str,
        timeout_seconds: int = ACCOUNT_TIMEOUT,
        global_deadline: Optional[GlobalDeadline] = None
    ):
        self.email = email
        self._timeout = timeout_seconds
        self._global = global_deadline
        self._start_time: Optional[float] = None
        self.metrics = TimingMetrics()
    
    def start(self) -> None:
        """Start account timer."""
        self._start_time = time.perf_counter()
    
    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0
        return time.perf_counter() - self._start_time
    
    @property
    def is_slow(self) -> bool:
        """Check if account is exceeding its time budget."""
        return self.elapsed_seconds >= self._timeout
    
    def check(self) -> None:
        """Raise if account or global deadline exceeded."""
        if self._global:
            self._global.check()
        if self.is_slow:
            raise TimeoutError(
                f"Account {self.email} exceeded timeout: "
                f"{self.elapsed_seconds:.1f}s >= {self._timeout}s"
            )
    
    def finalize(self) -> None:
        """Record final total time."""
        self.metrics.total_ms = int(self.elapsed_seconds * 1000)
    
    @asynccontextmanager
    async def timed_operation(self, name: str):
        """
        Context manager for timing operations.
        
        Usage:
            async with timer.timed_operation("login") as t:
                await do_login()
            timer.metrics.login_ms = t.elapsed_ms
        """
        self.check()
        t = Timer()
        t._start = time.perf_counter()
        try:
            yield t
        finally:
            t._end = time.perf_counter()


# Global singleton for deadline tracking
_global_deadline = GlobalDeadline()


def get_global_deadline() -> GlobalDeadline:
    """Get the global deadline instance."""
    return _global_deadline


def reset_global_deadline() -> None:
    """Reset and start a new global deadline."""
    global _global_deadline
    _global_deadline = GlobalDeadline()
    _global_deadline.start()
