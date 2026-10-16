"""Semantic analysis module for PathForge AST detection.

Provides deterministic feature extraction and pattern scoring that is
invariant to superficial code differences (loop forms, variable names,
AST shapes). Used in shadow mode alongside existing detectors.
"""
