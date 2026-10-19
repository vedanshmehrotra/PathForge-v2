"""Preview explicit cached corrections; --apply commits the supplied batch once.

Never part of app startup or /prepare-problem. Uses DATABASE_URL, does not run
migrations or call a model. Keep all input/output artifacts outside the repo.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, action="append")
    parser.add_argument("--apply", action="store_true", help="Explicitly commit the validated batch")
    args = parser.parse_args(argv)
    for path in args.package:
        if path.resolve() == ROOT or ROOT in path.resolve().parents:
            parser.error("Keep correction packages outside the repository")
    raw = None
    try:
        from pathforge.services.ground_truth_activation import stage_correction, validate_package
        packages = [json.loads(p.read_text(encoding="utf-8-sig")) for p in args.package]
        checked = [validate_package(package) for package in packages]
        ids = [package["problem_snapshot"]["id"] for package in checked]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate correction targets")
        import os
        import psycopg2
        from dotenv import load_dotenv
        from pathforge.db.db import PgConnection
        load_dotenv(ROOT / ".env", override=False)
        raw = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10, sslmode="require")
        raw.set_session(readonly=not args.apply, autocommit=False)
        connection = PgConnection(raw, None)
        connection.execute("SET LOCAL statement_timeout = '10s'")
        connection.execute("SET LOCAL lock_timeout = '5s'")
        results = [stage_correction(connection, package, apply=args.apply) for package in packages]
        if args.apply:
            raw.commit()
        else:
            raw.rollback()
        print(json.dumps({"state": "COMMITTED" if args.apply else "PREVIEW_ONLY",
                          "corrections": [{k: result[k] for k in
                              ("problem_id", "version", "package_sha256", "previous_sha256")} for result in results]}))
        return 0
    except Exception as error:
        if raw is not None:
            raw.rollback()
        # Driver messages can contain connection details; keep them out of logs.
        from pathforge.services.ground_truth_activation import CorrectionActivationError
        detail = str(error) if isinstance(error, CorrectionActivationError) else type(error).__name__
        print("Correction batch not committed: " + detail, file=sys.stderr)
        return 1
    finally:
        if raw is not None:
            raw.close()


if __name__ == "__main__":
    raise SystemExit(main())
