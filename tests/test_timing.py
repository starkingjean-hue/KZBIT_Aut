"""
Tests for timing module.
"""

import asyncio
import pytest
import time

from timing import Timer, GlobalDeadline, AccountTimer, TimingMetrics


class TestTimer:
    """Tests for the basic Timer class."""
    
    def test_timer_measures_time(self):
        """Timer should measure elapsed time."""
        with Timer() as t:
            time.sleep(0.1)
        
        assert t.elapsed_ms >= 90  # Allow some tolerance
        assert t.elapsed_ms < 200
    
    def test_timer_seconds(self):
        """Timer should report seconds correctly."""
        with Timer() as t:
            time.sleep(0.05)
        
        assert t.elapsed_seconds >= 0.04
        assert t.elapsed_seconds < 0.15


class TestGlobalDeadline:
    """Tests for GlobalDeadline enforcer."""
    
    def test_not_expired_before_timeout(self):
        """Should not be expired before timeout."""
        deadline = GlobalDeadline(timeout_seconds=1)
        deadline.start()
        
        assert not deadline.is_expired
        assert deadline.remaining_seconds > 0
    
    def test_expired_after_timeout(self):
        """Should be expired after timeout."""
        deadline = GlobalDeadline(timeout_seconds=0.1)
        deadline.start()
        time.sleep(0.15)
        
        assert deadline.is_expired
        assert deadline.remaining_seconds == 0
    
    def test_check_raises_when_expired(self):
        """Check should raise TimeoutError when expired."""
        deadline = GlobalDeadline(timeout_seconds=0.05)
        deadline.start()
        time.sleep(0.1)
        
        with pytest.raises(TimeoutError):
            deadline.check()
    
    def test_cancel_prevents_expiry(self):
        """Cancel should prevent expiry check."""
        deadline = GlobalDeadline(timeout_seconds=0.05)
        deadline.start()
        time.sleep(0.1)
        deadline.cancel()
        
        assert not deadline.is_expired


class TestTimingMetrics:
    """Tests for TimingMetrics dataclass."""
    
    def test_avg_submit_empty(self):
        """Average with no submits should be 0."""
        metrics = TimingMetrics()
        
        assert metrics.avg_submit_ms == 0
    
    def test_avg_submit_calculated(self):
        """Average should be calculated correctly."""
        metrics = TimingMetrics()
        metrics.submits_ms = [100, 200, 300]
        
        assert metrics.avg_submit_ms == 200
    
    def test_string_representation(self):
        """String should show all metrics."""
        metrics = TimingMetrics(
            login_ms=500,
            navigation_ms=100,
            submits_ms=[200, 300],
            total_ms=1100
        )
        
        s = str(metrics)
        assert "Login: 500ms" in s
        assert "Nav: 100ms" in s
        assert "Total: 1100ms" in s
