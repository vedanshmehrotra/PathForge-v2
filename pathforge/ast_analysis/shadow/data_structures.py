"""Core data structures for the shadow analysis path.

These are the canonical evidence contracts defined in
PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md.
"""
from dataclasses import dataclass, field
from typing import Optional


EXTRACTOR_VERSION = "1.0.0"


@dataclass
class StructuralFact:
    """A deterministic, mechanically decidable observation from the AST.

    Canonical persisted artifact. Higher-level labels are derived from these.
    """
    fact_id: str = ""
    fact_type: str = ""
    ast_ref: str = ""
    attributes: dict = field(default_factory=dict)
    extractor_version: str = EXTRACTOR_VERSION


@dataclass
class TechniqueEvidence:
    """Derived evidence for a reusable computational technique.

    Non-exclusive: a technique can appear in many strategies.
    presence_confidence and centrality are deliberately separate.
    """
    technique_id: str = ""
    technique_version: str = "1.0.0"
    supporting_fact_ids: list = field(default_factory=list)
    presence_confidence: float = 0.0
    centrality: float = 0.0


@dataclass
class StrategyEvidence:
    """Derived evidence for a higher-level algorithmic strategy.

    A strategy is inferred from technique evidence + structural constraints.
    primary_strategy is a projection and may be None.
    """
    strategy_id: str = ""
    strategy_version: str = "1.0.0"
    supporting_technique_ids: list = field(default_factory=list)
    supporting_fact_ids: list = field(default_factory=list)
    confidence: float = 0.0
    problem_context_signals: dict = field(default_factory=dict)


@dataclass
class MatchOutcome:
    """The result of solution-group satisfaction matching.

    Three possible outcomes: CONFIRMED, UNRESOLVED, CONTRADICTED.
    """
    outcome: str = "UNRESOLVED"
    satisfied_group_ids: list = field(default_factory=list)
    authority_tier: str = "unknown"
    technique_evidence: list = field(default_factory=list)
    strategy_evidence: list = field(default_factory=list)
    structural_facts: list = field(default_factory=list)
    primary_strategy: Optional[str] = None
    reasoning: list = field(default_factory=list)
