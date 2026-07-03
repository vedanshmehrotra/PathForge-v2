# src/ast_detection/run_analysis.py
"""Main entry point for the AST Analysis Engine."""

from typing import Dict, Any
from src.ast_detection.parser import Parser
from src.ast_detection.detector_manager import DetectorManager
from src.ast_detection.coordinator import Coordinator
from src.ast_detection.output_pipeline import OutputPipeline
from src.ast_detection.detector_interface import DetectionResult
class ASTAnalysisEngine:
    """Main class for the AST Analysis Engine.

    This class orchestrates the entire analysis pipeline:
    1. Parse Python source code into an AST
    2. Run all detectors on the AST
    3. Coordinate and filter detection results
    4. Package results into the final output structure

    The engine maintains the architecture's design principles:
    - Detectors never communicate with each other
    - Detectors never modify the AST
    - The coordinator performs no taxonomy reasoning
    - Confidence comes only from detector evidence
    - Output contains only detected patterns
    """

    def __init__(self):
        """Initialize the AST Analysis Engine."""
        self.parser = Parser()
        self.detector_manager = DetectorManager()
        self.coordinator = Coordinator()
        self.output_pipeline = OutputPipeline()

    def analyze(self, code_string: str) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline on Python source code.

        This is the main entry point for the AST Analysis Engine. It:
        1. Parses the source code into an AST
        2. Runs all detectors on the AST
        3. Coordinates and filters detection results
        4. Packages results into the final output structure

        Args:
            code_string: Python source code to analyze

        Returns:
            Dictionary containing the analysis results in the V2 format
        """
        # Step 1: Parse Python source code into AST
        ast_root = self.parser.parse(code_string)

        # Step 2: Run all detectors on the AST
        detection_results = self.detector_manager.detect_all(ast_root)

        # Step 3: Coordinate and filter detection results
        detected_patterns = self.coordinator.aggregate_and_filter(
            detection_results
        )

        # Step 4: Package results into the final output structure
        final_output = self.output_pipeline.package_results(detected_patterns)

        return final_output

    def analyze_with_results(self, code_string: str) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline and return intermediate results.

        This method provides access to intermediate results for testing and
        debugging purposes. It returns a dictionary containing all stages
        of the analysis process.

        Args:
            code_string: Python source code to analyze

        Returns:
            Dictionary containing intermediate results and final output
        """
        # Step 1: Parse Python source code into AST
        ast_root = self.parser.parse(code_string)

        # Step 2: Run all detectors on the AST
        all_detection_results = self.detector_manager.detect_all(ast_root)

        # Step 3: Coordinate and filter detection results
        detected_patterns = self.coordinator.aggregate_and_filter(
            all_detection_results
        )

        # Step 4: Package results into the final output structure
        final_output = self.output_pipeline.package_results(detected_patterns)

        return {
            "ast_root": ast_root,
            "all_detection_results": all_detection_results,
            "detected_patterns": detected_patterns,
            "final_output": final_output,
        }

    def get_detector_count(self) -> int:
        """
        Get the number of registered detectors.

        Returns:
            Number of detectors
        """
        return self.detector_manager.get_detector_count()

    def validate_code(self, code_string: str) -> bool:
        """
        Validate Python code syntax and safety.

        Args:
            code_string: Python source code to validate

        Returns:
            True if code is valid and safe, False otherwise
        """
        return self.parser.is_valid_python(code_string) and self.parser.is_safe_code(
            code_string
        )
# Convenience function for backward compatibility
def run_analysis(code_string: str) -> Dict[str, Any]:
    """
    Run analysis on Python source code.

    This is the convenience function for the AST Analysis Engine.
    It parses the source code, runs all detectors, and returns the
    analysis results.

    Args:
        code_string: Python source code to analyze

    Returns:
        Dictionary containing the analysis results in the V2 format
    """
    engine = ASTAnalysisEngine()
    return engine.analyze(code_string)