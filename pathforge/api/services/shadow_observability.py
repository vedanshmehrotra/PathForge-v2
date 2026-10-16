"""Shadow-mode observability for production monitoring.

Tracks aggregate counts of shadow analysis behavior without storing
raw code or individual submission data. Designed for lightweight
structured logging that can be aggregated by log analysis tools.

All counters are in-memory and reset on process restart. For persistent
monitoring, integrate with your logging/monitoring stack.

Two pipeline counters exist:
- ShadowCounters: hybrid/semantic shadow detector (legacy)
- ShadowPipelineCounters: fact/technique/strategy shadow pipeline (pilot)
"""
import time
import threading
import bisect
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================
# Hybrid Shadow Counters (legacy)
# ============================================================

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


# ============================================================
# Shadow Pipeline Counters (fact/technique/strategy pilot)
# ============================================================

# Maximum number of latency samples to retain for percentile computation
_MAX_LATENCY_SAMPLES = 10000


@dataclass
class ConfirmedRecord:
    """Observational metadata for a single CONFIRMED shadow result.

    No raw user code or PII is stored.
    """
    code_hash: str = ""
    strategy_id: str = ""
    satisfied_group_ids: list = field(default_factory=list)
    satisfaction_score: float = 0.0
    authority_tier: str = ""
    extractor_version: str = ""
    technique_def_version: str = ""
    strategy_def_version: str = ""
    elapsed_ms: float = 0.0
    techniques_detected: list = field(default_factory=list)
    strategies_detected: list = field(default_factory=list)


@dataclass
class ShadowPipelineCounters:
    """Aggregate counters for the fact/technique/strategy shadow pipeline.

    Tracks: total analyses, confirmed/unresolved/contradictions,
    strategy breakdown, latency percentiles, extraction rates.
    """

    # --- Outcome counts ---
    total_analyses: int = 0
    confirmed: int = 0
    unresolved: int = 0
    contradictions: int = 0

    # --- Failure counts ---
    parse_failures: int = 0
    extraction_failures: int = 0  # no facts extracted

    # --- Strategy breakdown ---
    confirmed_by_strategy: Dict[str, int] = field(default_factory=dict)
    unresolved_by_strategy: Dict[str, int] = field(default_factory=dict)

    # --- Unresolved categorization ---
    unresolved_by_category: Dict[str, int] = field(default_factory=dict)
    # Categories: "no_groups", "no_technique_match", "no_strategy_match",
    #             "below_threshold", "excluded_evidence", "parse_failure", "empty_extraction"

    # --- Extraction rates (computed on demand) ---
    technique_detection_rate: float = 0.0
    strategy_detection_rate: float = 0.0

    # --- Latency tracking (sorted list for percentile computation) ---
    _latency_samples: List[float] = field(default_factory=list)
    _latency_sorted: List[float] = field(default_factory=list)

    # --- Confirmed record buffer (circular, last 200) ---
    _confirmed_records: List[ConfirmedRecord] = field(default_factory=list)
    _max_confirmed_records: int = 200

    def record_analysis(
        self,
        outcome: str,
        elapsed_ms: float,
        strategy_id: Optional[str] = None,
        satisfaction_score: float = 0.0,
        satisfied_group_ids: Optional[list] = None,
        authority_tier: str = "",
        techniques_detected: Optional[list] = None,
        strategies_detected: Optional[list] = None,
        extractor_version: str = "",
        technique_def_version: str = "",
        strategy_def_version: str = "",
        code_hash: str = "",
        has_groups: bool = True,
        has_techniques: bool = False,
        has_strategies: bool = False,
        unresolved_category: Optional[str] = None,
    ) -> None:
        """Record a single shadow analysis result.

        Thread-safe: must be called under the module-level lock.
        """
        self.total_analyses += 1

        # Record latency
        self._record_latency(elapsed_ms)

        # Record outcome
        if outcome == "CONFIRMED":
            self.confirmed += 1
            if strategy_id:
                self.confirmed_by_strategy[strategy_id] = (
                    self.confirmed_by_strategy.get(strategy_id, 0) + 1
                )
            # Store confirmed record (circular buffer)
            record = ConfirmedRecord(
                code_hash=code_hash,
                strategy_id=strategy_id or "",
                satisfied_group_ids=satisfied_group_ids or [],
                satisfaction_score=satisfaction_score,
                authority_tier=authority_tier,
                extractor_version=extractor_version,
                technique_def_version=technique_def_version,
                strategy_def_version=strategy_def_version,
                elapsed_ms=elapsed_ms,
                techniques_detected=techniques_detected or [],
                strategies_detected=strategies_detected or [],
            )
            self._confirmed_records.append(record)
            if len(self._confirmed_records) > self._max_confirmed_records:
                self._confirmed_records = self._confirmed_records[-self._max_confirmed_records:]

        elif outcome == "UNRESOLVED":
            self.unresolved += 1
            if strategy_id:
                self.unresolved_by_strategy[strategy_id] = (
                    self.unresolved_by_strategy.get(strategy_id, 0) + 1
                )
            if unresolved_category:
                self.unresolved_by_category[unresolved_category] = (
                    self.unresolved_by_category.get(unresolved_category, 0) + 1
                )

        elif outcome == "CONTRADICTED":
            self.contradictions += 1

    def record_parse_failure(self) -> None:
        """Record a parse failure."""
        self.total_analyses += 1
        self.parse_failures += 1

    def record_extraction_failure(self) -> None:
        """Record an extraction failure (no facts extracted)."""
        self.extraction_failures += 1

    def _record_latency(self, elapsed_ms: float) -> None:
        """Record a latency sample, maintaining a sorted list for percentiles."""
        self._latency_samples.append(elapsed_ms)
        bisect.insort(self._latency_sorted, elapsed_ms)
        # Trim to max samples
        if len(self._latency_sorted) > _MAX_LATENCY_SAMPLES:
            # Remove oldest samples (from front)
            excess = len(self._latency_sorted) - _MAX_LATENCY_SAMPLES
            self._latency_samples = self._latency_samples[excess:]
            self._latency_sorted = self._latency_sorted[excess:]

    def get_latency_percentiles(self) -> dict:
        """Compute latency percentiles from collected samples."""
        if not self._latency_sorted:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0, "samples": 0}

        n = len(self._latency_sorted)
        return {
            "p50_ms": round(self._latency_sorted[int(n * 0.5)], 2),
            "p95_ms": round(self._latency_sorted[min(int(n * 0.95), n - 1)], 2),
            "p99_ms": round(self._latency_sorted[min(int(n * 0.99), n - 1)], 2),
            "max_ms": round(self._latency_sorted[-1], 2),
            "samples": n,
        }

    def to_log_dict(self) -> dict:
        """Convert counters to a structured dict for logging."""
        latency = self.get_latency_percentiles()
        return {
            "shadow_pipeline": {
                "total_analyses": self.total_analyses,
                "confirmed": self.confirmed,
                "unresolved": self.unresolved,
                "contradictions": self.contradictions,
                "parse_failures": self.parse_failures,
                "extraction_failures": self.extraction_failures,
                "confirmed_by_strategy": dict(self.confirmed_by_strategy),
                "unresolved_by_strategy": dict(self.unresolved_by_strategy),
                "unresolved_by_category": dict(self.unresolved_by_category),
                "latency": latency,
            }
        }

    def get_recent_confirmed(self, n: int = 10) -> list:
        """Get the most recent N confirmed records for inspection."""
        return self._confirmed_records[-n:]

    def reset(self) -> None:
        """Reset all counters. Use with caution — for pilot restart only."""
        self.total_analyses = 0
        self.confirmed = 0
        self.unresolved = 0
        self.contradictions = 0
        self.parse_failures = 0
        self.extraction_failures = 0
        self.confirmed_by_strategy.clear()
        self.unresolved_by_strategy.clear()
        self.unresolved_by_category.clear()
        self._latency_samples.clear()
        self._latency_sorted.clear()
        self._confirmed_records.clear()


# ============================================================
# Global singletons and thread-safe accessors
# ============================================================

_shadow_counters = ShadowCounters()
_pipeline_counters = ShadowPipelineCounters()
_lock = threading.Lock()


def get_shadow_counters() -> ShadowCounters:
    """Get the global hybrid shadow counters (thread-safe)."""
    return _shadow_counters


def get_pipeline_counters() -> ShadowPipelineCounters:
    """Get the global shadow pipeline counters (thread-safe)."""
    return _pipeline_counters


def record_shadow_result(shadow_result) -> None:
    """Record a hybrid shadow result in the global counters (thread-safe)."""
    with _lock:
        _shadow_counters.update_from_shadow(shadow_result)


def record_shadow_pipeline_result(**kwargs) -> None:
    """Record a shadow pipeline analysis result (thread-safe).

    Accepts keyword arguments matching ShadowPipelineCounters.record_analysis().
    """
    with _lock:
        _pipeline_counters.record_analysis(**kwargs)


def record_shadow_parse_failure() -> None:
    """Record a shadow pipeline parse failure (thread-safe)."""
    with _lock:
        _pipeline_counters.record_parse_failure()


def record_shadow_extraction_failure() -> None:
    """Record a shadow pipeline extraction failure (thread-safe)."""
    with _lock:
        _pipeline_counters.record_extraction_failure()


def get_shadow_log_dict() -> dict:
    """Get current shadow counters as a loggable dict (thread-safe)."""
    with _lock:
        return _shadow_counters.to_log_dict()


def get_pipeline_log_dict() -> dict:
    """Get current shadow pipeline counters as a loggable dict (thread-safe)."""
    with _lock:
        return _pipeline_counters.to_log_dict()


def get_shadow_observability_log() -> dict:
    """Get combined shadow observability log (both pipelines, thread-safe)."""
    with _lock:
        return {
            **_shadow_counters.to_log_dict(),
            **_pipeline_counters.to_log_dict(),
        }
