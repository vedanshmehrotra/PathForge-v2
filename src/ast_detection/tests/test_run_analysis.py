"""Integration tests for the complete AST Analysis Engine pipeline."""

import pytest
from src.ast_detection.run_analysis import run_analysis, ASTAnalysisEngine


class TestRunAnalysis:
    def test_run_analysis_basic(self):
        """Test run_analysis with simple Python code."""
        result = run_analysis("x = 1 + 2")
        assert "detected_patterns" in result
        assert "engine_version" in result
        assert "analyzed_at" in result
        assert "patterns_checked" in result
        assert "patterns_detected" in result
        assert result["engine_version"] == "2.0.0"

    def test_run_analysis_no_patterns_detected(self):
        """Test run_analysis returns no patterns for simple code."""
        result = run_analysis("x = 1")
        assert len(result["detected_patterns"]) == 0
        assert result["patterns_detected"] == 0

    def test_run_analysis_function(self):
        """Test run_analysis with function definition."""
        result = run_analysis("def foo(x): return x")
        assert result["engine_version"] == "2.0.0"

    def test_run_analysis_class(self):
        """Test run_analysis with class definition."""
        result = run_analysis("class Foo: pass")
        assert result["engine_version"] == "2.0.0"

    def test_run_analysis_invalid_syntax(self):
        """Test run_analysis raises ValueError for invalid syntax."""
        with pytest.raises(ValueError, match="Invalid Python syntax"):
            run_analysis("def foo(")

    def test_run_analysis_empty_code(self):
        """Test run_analysis raises ValueError for empty code."""
        with pytest.raises(ValueError, match="cannot be empty"):
            run_analysis("")

    def test_run_analysis_unsafe_eval(self):
        """Test run_analysis rejects unsafe eval."""
        with pytest.raises(ValueError, match="Unsafe construct"):
            run_analysis("eval('1+1')")

    def test_run_analysis_unsafe_exec(self):
        """Test run_analysis rejects unsafe exec."""
        with pytest.raises(ValueError, match="Unsafe construct"):
            run_analysis("exec('import os')")

    def test_run_analysis_dangerous_import(self):
        """Test run_analysis rejects dangerous imports."""
        with pytest.raises(ValueError, match="Dangerous import"):
            run_analysis("import subprocess")


class TestASTAnalysisEngine:
    def test_engine_initialization(self):
        """Test ASTAnalysisEngine initializes correctly."""
        engine = ASTAnalysisEngine()
        assert engine.parser is not None
        assert engine.detector_manager is not None
        assert engine.coordinator is not None
        assert engine.output_pipeline is not None

    def test_engine_analyze(self):
        """Test ASTAnalysisEngine.analyze method."""
        engine = ASTAnalysisEngine()
        result = engine.analyze("x = 1")
        assert "detected_patterns" in result

    def test_engine_analyze_with_results(self):
        """Test ASTAnalysisEngine.analyze_with_results method."""
        engine = ASTAnalysisEngine()
        result = engine.analyze_with_results("x = 1")
        assert "ast_root" in result
        assert "all_detection_results" in result
        assert "detected_patterns" in result
        assert "final_output" in result

    def test_engine_get_detector_count(self):
        """Test ASTAnalysisEngine.get_detector_count."""
        engine = ASTAnalysisEngine()
        assert engine.get_detector_count() >= 3

    def test_engine_validate_code_valid(self):
        """Test ASTAnalysisEngine.validate_code with valid code."""
        engine = ASTAnalysisEngine()
        assert engine.validate_code("x = 1") == True

    def test_engine_validate_code_invalid(self):
        """Test ASTAnalysisEngine.validate_code with invalid code."""
        engine = ASTAnalysisEngine()
        assert engine.validate_code("def foo(") == False
        assert engine.validate_code("") == False
