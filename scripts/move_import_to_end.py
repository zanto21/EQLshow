#!/usr/bin/env python3
"""
Move a specific top-level import statement to the end of a file.

Background:
Some modules in giskardpy import another module near the top of the file,
before defining a class that the imported module needs to import back. This
creates a genuine circular import: as soon as the importing module reaches
the early import line, Python starts loading the other module, which tries
to import a name that has not been defined yet in the still-loading file.

Moving the import to the very end of the file (after every class in the
file has been fully defined) breaks the cycle in the safest, most general
way: whatever the other module needs to import back is guaranteed to
already exist by then, regardless of how many names it needs or where they
are defined within this file.

Usage:
    python3 move_import_to_end.py <path_to_file.py> "<exact import line>"

Example:
    python3 move_import_to_end.py \\
        giskardpy/motion_statechart/graph_node.py \\
        "from giskardpy.motion_statechart.constraint_builders import GeometricConstraintBuilder"
"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print('Usage: python3 move_import_to_end.py <path_to_file.py> "<exact import line>"')
        sys.exit(1)

    path = Path(sys.argv[1])
    import_text = sys.argv[2].strip()
    import_line = import_text + "\n"

    lines = path.read_text().splitlines(keepends=True)

    matching_indices = [
        i for i, line in enumerate(lines) if line.strip() == import_text
    ]
    if not matching_indices:
        print(f"Import line not found in {path}: {import_text!r}")
        sys.exit(1)
    if len(matching_indices) > 1:
        print(
            f"Warning: found {len(matching_indices)} occurrences of the import "
            f"line in {path}; removing all of them and appending one copy at "
            f"the end."
        )

    lines = [line for i, line in enumerate(lines) if i not in matching_indices]

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    lines.append("\n")
    lines.append(import_line)

    path.write_text("".join(lines))
    print(f"Moved '{import_text}' to the end of {path}.")


if __name__ == "__main__":
    main()
