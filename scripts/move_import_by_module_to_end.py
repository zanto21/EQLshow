#!/usr/bin/env python3
"""
Move a top-level import statement, identified by its module name, to the
end of a file.

Background:
Some modules in giskardpy import a sibling module near the top of the file,
before defining a class that the imported module needs to import back. This
creates a genuine circular import. Moving the import to the end of the file
(after every class in the file has been fully defined) breaks the cycle,
since whatever the other module needs to import back is guaranteed to
already exist by then.

Unlike a plain text-line match, this script uses the `ast` module to find
the import by its module name, so it correctly handles multi-line
parenthesized imports such as

    from foo.bar import (
        A,
        B,
    )

and moves the exact original text (including its original formatting) to
the end of the file.

Usage:
    python3 move_import_by_module_to_end.py <path_to_file.py> <module_name>

Example:
    python3 move_import_by_module_to_end.py \\
        giskardpy/motion_statechart/graph_node.py \\
        giskardpy.motion_statechart.exceptions
"""

import ast
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 move_import_by_module_to_end.py <path_to_file.py> <module_name>")
        sys.exit(1)

    path = Path(sys.argv[1])
    module_name = sys.argv[2]

    source = path.read_text()
    tree = ast.parse(source)

    matching_nodes = [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.ImportFrom) and node.module == module_name
    ]
    if not matching_nodes:
        print(f"No top-level 'from {module_name} import ...' found in {path}; nothing to do.")
        sys.exit(1)

    lines = source.splitlines(keepends=True)
    ranges = [(node.lineno, node.end_lineno) for node in matching_nodes]

    moved_texts = ["".join(lines[start - 1:end]) for start, end in ranges]
    lines_to_remove = {i for start, end in ranges for i in range(start - 1, end)}
    remaining_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]

    if remaining_lines and not remaining_lines[-1].endswith("\n"):
        remaining_lines[-1] += "\n"

    remaining_lines.append("\n")
    remaining_lines.extend(moved_texts)

    path.write_text("".join(remaining_lines))
    print(f"Moved import from '{module_name}' to the end of {path}.")


if __name__ == "__main__":
    main()
