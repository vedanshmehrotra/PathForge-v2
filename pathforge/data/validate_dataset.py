import csv
import json
import os
import sys

# Add pathforge directory to path so we can import patterns
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from pathforge.ast_engine.patterns import ALL_PATTERNS

def validate_dataset():
    csv_path = os.path.join(os.path.dirname(__file__), "pathforge_problems_fixed.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Dataset file not found at {csv_path}")
        sys.exit(1)
        
    print(f"Loading and validating {csv_path}...")
    errors = 0
    total_problems = 0
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_problems += 1
            pattern_str = row.get('pattern', '[]')
            try:
                patterns = json.loads(pattern_str)
                for p in patterns:
                    if p not in ALL_PATTERNS:
                        print(f"Row ID {row.get('ID')}: Pattern '{p}' is not defined in patterns.py!")
                        errors += 1
            except Exception as e:
                print(f"Row ID {row.get('ID')}: Failed to parse pattern string '{pattern_str}': {e}")
                errors += 1
                
    if errors > 0:
        print(f"Validation FAILED: {errors} error(s) found across {total_problems} problems.")
        sys.exit(1)
    else:
        print(f"Validation SUCCESS: All {total_problems} problems verified. All pattern labels match patterns.py.")

if __name__ == "__main__":
    validate_dataset()
