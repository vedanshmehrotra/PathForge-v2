"""Shadow-mode observability for production monitoring.

Tracks aggregate counts of hybrid detection behavior without storing
raw code or individual submission data. Designed for lightweight
structured logging that can be aggregated by log analysis tools.

All counters are in-memory and reset on process restart. For persistent
monitoring, integrate with your logging/monitoring stack.
"""
import time
import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ShadowCounters:
    """Aggregate counters for shadow-mode observability."""

    # Total analyses
    total_analyses: int = 0
    semantic_failures: int = 0

    # Discrepancy counts (across all patterns)
    semantic_only_detections: int = 0
    ast_only_detections: int = 0
    agreements: int = 0
    conflicts: int = 0

    # Per-pattern counts
    pattern_hybrid_changes: Dict[str, int] = field(default_factory=dict)
    pattern_semantic_only: Dict[str, int] = field(default_factory=dict)
    pattern_conflicts: Dict[str, int] = field(default_factory=dict)

    # Latency (rolling average via exponential moving average)
    ast_latency_ema: float = 0.0
    sem_latency_ema: float = 0.0
    total_latency_ema: float = 0.0
    latency_samples: int = 0

    # EMA smoothing factor
    _ema_alpha: float = 0.1

    def update_from_shadow(self, shadow_result) -> None:
        """Update counters from a ShadowResult."""
        if shadow_result is None:
            self.semantic_failures += 1
            return

        self.total_analyses += 1

        # Update latency EMA
        self.latency_samples += 1
        alpha = self._ema_alpha
        if self.latency_samples == 1:
            self.ast_latency_ema = shadow_result.ast_latency_ms
            self.sem_latency_ema = shadow_result.sem_latency_ms
            self.total_latency_ema = shadow_result.total_latency_ms
        else:
            self.ast_latency_ema = alpha * shadow_result.ast_latency_ms + (1 - alpha) * self.ast_latency_ema
            self.sem_latency_ema = alpha * shadow_result.sem_latency_ms + (1 - alpha) * self.sem_latency_ema
            self.total_latency_ema = alpha * shadow_result.total_latency_ms + (1 - alpha) * self.total_latency_ema

        # Count discrepancies
        for disc in shadow_result.discrepancies:
            dtype = disc.discrepancy_type
            pid = disc.pattern_id

            if dtype == "semantic_only":
                self.semantic_only_detections += 1
                self.pattern_semantic_only[pid] = self.pattern_semantic_only.get(pid, 0) + 1
            elif dtype == "ast_only":
                self.ast_only_detections += 1
            elif dtype == "both":
                self.agreements += 1
            elif dtype == "conflict":
                self.conflicts += 1
                self.pattern_conflicts[pid] = self.pattern_conflicts.get(pid, 0) + 1

            # Track hybrid changes (any pattern where hybrid != AST)
            if disc.hybrid_detected != disc.ast_detected:
                self.pattern_hybrid_changes[pid] = self.pattern_hybrid_changes.get(pid, 0) + 1

    def to_log_dict(self) -> dict:
        """Convert counters to a structured dict for logging."""
        return {
            "shadow": {
                "total_analyses": self.total_analyses,
                "semantic_failures": self.semantic_failures,
                "semantic_only": self.semantic_only_detections,
                "ast_only": self.ast_only_detections,
                "agreements": self.agreements,
                "conflicts": self.conflicts,
                "hybrid_changes": dict(self.pattern_hybrid_changes),
                "pattern_semantic_only": dict(self.pattern_semantic_only),
                "pattern_conflicts": dict(self.pattern_conflicts),
                "latency": {
                    "ast_ms": round(self.ast_latency_ema, 2),
                    "semantic_ms": round(self.sem_latency_ema, 2),
                    "total_ms": round(self.total_latency_ema, 2),
                    "samples": self.latency_samples,
                },
            }
        }


# Global singleton for in-process counters
_shadow_counters = ShadowCounters()
_lock = threading.Lock()


def get_shadow_counters() -> ShadowCounters:
    """Get the global shadow counters (thread-safe)."""
    return _shadow_counters


def record_shadow_result(shadow_result) -> None:
    """Record a shadow result in the global counters (thread-safe)."""
    with _lock:
        _shadow_counters.update_from_shadow(shadow_result)


def get_shadow_log_dict() -> dict:
    """Get current shadow counters as a loggable dict (thread-safe)."""
    with _lock:
        return _shadow_counters.to_log_dict()
