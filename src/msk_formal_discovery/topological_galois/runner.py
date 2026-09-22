"""Build or validate the 01A artifact package.

  python -m msk_formal_discovery.topological_galois.runner --write     regenerate every artifact (needs sympy for the target domain)
  python -m msk_formal_discovery.topological_galois.runner --check     recompute and compare with the committed package
"""
from __future__ import annotations

import argparse
import sys

from . import qualification as q


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.write:
        from . import target_domain
        files = q.build_artifacts(target_domain.derive_all())
        q.write_artifacts(files)
        print(f"wrote {len(files)} artifacts to {q.EXPERIMENT_DIR}; result = {files['qualification-result.v0.1.json']['disposition']}")
    if args.check or not args.write:
        errors = q.validate()
        if errors:
            print("FAILED:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        res = q.load_artifacts()["qualification-result.v0.1.json"]
        print(f"PASS: {res['disposition']} | BURAU_ROLE={res['BURAU_ROLE']} | hostile all rejected as stated={res['hostile_controls_all_rejected_as_stated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
