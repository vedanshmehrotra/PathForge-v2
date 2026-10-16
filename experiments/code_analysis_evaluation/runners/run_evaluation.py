"""Run evaluation of both analysis systems on the test dataset.

This script:
1. Loads submissions from the dataset
2. Runs legacy (AST) analysis on each
3. Runs shadow (fact/technique/strategy) analysis on each
4. Saves raw outputs for metric calculation
5. Handles errors gracefully without modifying production code

Does NOT modify any production scoring, ELO, or recommendation logic.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ast_detection.run_analysis import ASTAnalysisEngine
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


class EvaluationRunner:
    """Runs both analysis systems and collects raw outputs."""
    
    def __init__(self):
        self.ast_engine = ASTAnalysisEngine()
        self.results = []
        self.errors = []
    
    def run_legacy_analysis(self, code: str) -> dict:
        """Run the legacy AST analysis engine."""
        try:
            t0 = time.perf_counter()
            result = self.ast_engine.analyze(code)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            
            return {
                "success": True,
                "elapsed_ms": round(elapsed_ms, 2),
                "detected_patterns": result.get("detected_patterns", []),
                "detection_summary": result.get("detection_summary", {}),
                "raw_output": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }
    
    def run_shadow_analysis(self, code: str, solution_groups: Optional[list] = None) -> dict:
        """Run the shadow analysis path."""
        try:
            result = run_shadow_analysis(code, solution_groups=solution_groups)
            if result is None:
                return {
                    "success": False,
                    "error": "Shadow analysis returned None (parse failure or exception)",
                    "error_type": "SHADOW_RETURNED_NONE",
                }
            return {
                "success": True,
                **result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }
    
    def evaluate_submission(self, submission: dict) -> dict:
        """Run both analysis systems on a single submission."""
        sub_id = submission["submission_id"]
        code = submission["source_code"]
        
        result = {
            "submission_id": sub_id,
            "problem_id": submission.get("problem_id"),
            "problem_title": submission.get("problem_title", ""),
            "target_concepts": submission.get("target_concepts", []),
            "solution_correctness": submission.get("solution_correctness", "unknown"),
            "style": submission.get("style", "standard"),
            "variant": submission.get("variant"),
            "legacy": self.run_legacy_analysis(code),
            "shadow": self.run_shadow_analysis(code),
        }
        
        return result
    
    def extract_legacy_concepts(self, legacy_result: dict) -> list:
        """Extract detected concept IDs from legacy analysis result."""
        if not legacy_result.get("success"):
            return []
        
        patterns = legacy_result.get("detected_patterns", [])
        concepts = []
        for pattern in patterns:
            pid = pattern.get("pattern_id", "")
            conf = pattern.get("confidence", 0.0)
            evidence = pattern.get("evidence", [])
            # Output pipeline only includes detected patterns
            if conf > 0.0 or evidence:
                concepts.append(pid)
        return concepts
    
    def extract_shadow_concepts(self, shadow_result: dict) -> list:
        """Extract detected concept IDs from shadow analysis result."""
        if not shadow_result.get("success"):
            return []
        
        concepts = []
        
        # Extract from technique evidence
        for tech in shadow_result.get("technique_evidence", []):
            tid = tech.get("technique_id", "")
            if tid:
                concepts.append(tid)
        
        # Extract from strategy evidence
        for strat in shadow_result.get("strategy_evidence", []):
            sid = strat.get("strategy_id", "")
            if sid:
                concepts.append(sid)
        
        # Extract from match outcome
        outcome = shadow_result.get("match_outcome", {})
        if outcome.get("primary_strategy"):
            concepts.append(outcome["primary_strategy"])
        
        return list(set(concepts))
    
    def run_dataset(self, dataset_path: str, output_dir: str) -> dict:
        """Run evaluation on the entire dataset."""
        os.makedirs(output_dir, exist_ok=True)
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            submissions = json.load(f)
        
        print(f"Running evaluation on {len(submissions)} submissions...")
        
        all_results = []
        legacy_success = 0
        shadow_success = 0
        legacy_errors = 0
        shadow_errors = 0
        
        for i, sub in enumerate(submissions):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(submissions)}")
            
            result = self.evaluate_submission(sub)
            all_results.append(result)
            
            # Track success rates
            if result["legacy"]["success"]:
                legacy_success += 1
            else:
                legacy_errors += 1
            
            if result["shadow"]["success"]:
                shadow_success += 1
            else:
                shadow_errors += 1
        
        # Save raw results
        raw_path = os.path.join(output_dir, "raw_results.json")
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Create summary
        summary = {
            "total_submissions": len(submissions),
            "legacy_success": legacy_success,
            "legacy_errors": legacy_errors,
            "shadow_success": shadow_success,
            "shadow_errors": shadow_errors,
            "legacy_success_rate": legacy_success / len(submissions) if submissions else 0,
            "shadow_success_rate": shadow_success / len(submissions) if submissions else 0,
        }
        
        summary_path = os.path.join(output_dir, "evaluation_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nEvaluation complete:")
        print(f"  Total: {summary['total_submissions']}")
        print(f"  Legacy success: {summary['legacy_success']} ({summary['legacy_success_rate']:.1%})")
        print(f"  Shadow success: {summary['shadow_success']} ({summary['shadow_success_rate']:.1%})")
        print(f"  Results saved to: {output_dir}")
        
        return summary


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    dataset_path = str(base_dir / "dataset" / "selected_submissions" / "submissions.json")
    output_dir = str(base_dir / "results" / "raw_outputs")
    
    if not os.path.exists(dataset_path):
        print("Dataset not found. Running build_dataset first...")
        from build_dataset import build_dataset, load_problems_csv
        csv_path = str(PROJECT_ROOT / "pathforge" / "data" / "pathforge_problems_fixed.csv")
        build_dataset(csv_path, str(base_dir / "dataset" / "selected_submissions"), max_submissions=200)
    
    runner = EvaluationRunner()
    summary = runner.run_dataset(dataset_path, output_dir)
