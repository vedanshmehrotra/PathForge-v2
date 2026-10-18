"""Prepare an offline correction package; never connect, generate or activate.

python -B scripts/prepare_ground_truth_correction.py --input request.json --output <external-file.json>
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    destination = args.output.resolve()
    if destination == ROOT or ROOT in destination.parents:
        parser.error("Keep exported ground truth and generated packages outside the repository")
    from pathforge.services.ground_truth_correction import CorrectionPreparationError, prepare_correction
    from pathforge.services.ground_truth_builder import GroundTruthError

    try:
        request = json.loads(args.input.read_text(encoding="utf-8-sig"))
        package = prepare_correction(request)
        # Exclusive creation: preserve existing evidence, including the input.
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(package, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    except (CorrectionPreparationError, GroundTruthError) as error:
        print(f"Correction not prepared: {error}. No database changes.", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("Correction not prepared: invalid input, generation output, or output destination. No database changes.",
              file=sys.stderr)
        return 1
    print("Prepared an inactive proposed correction package. No database or model calls; no data activated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
