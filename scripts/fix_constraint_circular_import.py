#!/usr/bin/env python3
"""
Break the circular import between giskardpy's constraint.py and
enforcement_strategy.py without removing type information krrood needs.

Background:
constraint.py defines several classes (GiskardConstraint,
GiskardEqualityConstraint, GiskardInequalityConstraint, ...) and only
imports EnforcementStrategy from enforcement_strategy.py inside a
TYPE_CHECKING block, since enforcement_strategy.py itself imports multiple
of those classes back from constraint.py unconditionally at module level.

krrood's runtime ORM generation needs EnforcementStrategy to be actually
importable in constraint.py's namespace, not just available to static type
checkers. Promoting the TYPE_CHECKING import naively (placed near the top of
the file, or even right after a single class definition) creates a genuine
runtime circular import, because enforcement_strategy.py may import several
different classes from constraint.py that are not all defined yet at that
point in the file.

The fix: append the unconditional import of EnforcementStrategy at the very
end of constraint.py. By then, every class constraint.py defines already
exists in its module namespace, so enforcement_strategy.py's back-import of
any of them succeeds regardless of how many classes it needs, and
EnforcementStrategy ends up defined in constraint.py's namespace by the time
the module has finished loading (which is all krrood's later type hint
resolution requires). The original TYPE_CHECKING-only import is left in
place; having both is harmless, since the TYPE_CHECKING block is never
executed at runtime.

Usage:
    python3 fix_constraint_circular_import.py <path_to_constraint.py>
"""

import sys
from pathlib import Path

IMPORT_LINE = "from giskardpy.qp.enforcement_strategy import EnforcementStrategy\n"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 fix_constraint_circular_import.py <path_to_constraint.py>")
        sys.exit(1)

    path = Path(sys.argv[1])
    lines = path.read_text().splitlines(keepends=True)

    # Remove any unconditional (unindented) copy of the import that may have
    # been inserted earlier at the wrong position, by the general
    # TYPE_CHECKING patch or a previous run of this script. The original
    # TYPE_CHECKING-only import stays untouched, since that copy is indented
    # and therefore does not match this exact line.
    lines = [line for line in lines if line != IMPORT_LINE]

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    lines.append("\n")
    lines.append(IMPORT_LINE)

    path.write_text("".join(lines))
    print(f"Appended the unconditional import of EnforcementStrategy at the end of {path}.")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()

