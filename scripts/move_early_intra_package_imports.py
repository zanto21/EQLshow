#!/usr/bin/env python3
"""
Move all early intra-package imports in a file to the end of the file.

Background:
graph_node.py in giskardpy's motion_statechart module imports several
sibling modules (context, exceptions, data_types, error_signals, ...) near
the top of the file, before it defines `class MotionStatechartNode`. Several
of those sibling modules, directly or indirectly, try to import
MotionStatechartNode back from graph_node.py. Each such early import
therefore triggers its own circular import failure, one at a time, as soon
as the previous one is fixed.

Rather than moving each import individually (which requires one Docker
build per occurrence to discover), this script moves every top-level import
statement that targets a module inside the same top-level package (e.g.
every `from giskardpy...` import in a file that itself belongs to the
giskardpy package) and that appears before the target class definition, to
the end of the file in one pass. Imports of external packages (numpy,
krrood, semantic_digital_twin, standard library, ...) are left untouched,
since those are not part of the circular dependency.

Usage:
    python3 move_early_intra_package_imports.py <path_to_file.py> <package_prefix> <target_class>

Example:
    python3 move_early_intra_package_imports.py \\
        giskardpy/motion_statechart/graph_node.py \\
        giskardpy \\
        MotionStatechartNode
"""

import ast
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python3 move_early_intra_package_imports.py "
            "<path_to_file.py> <package_prefix> <target_class>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])
    package_prefix = sys.argv[2]
    target_class = sys.argv[3]

    source = path.read_text()
    tree = ast.parse(source)

    class_node = next(
        (
            node for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.ClassDef) and node.name == target_class
        ),
        None,
    )
    if class_node is None:
        print(f"Could not find 'class {target_class}' in {path}; nothing to do.")
        sys.exit(1)

    class_start_line = class_node.lineno

    movable_ranges: list[tuple[int, int]] = []
    for node in ast.iter_child_nodes(tree):
        if node.lineno >= class_start_line:
            continue
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(package_prefix):
            movable_ranges.append((node.lineno, node.end_lineno))
        elif isinstance(node, ast.Import) and any(
            alias.name.startswith(package_prefix) for alias in node.names
        ):
            movable_ranges.append((node.lineno, node.end_lineno))

    if not movable_ranges:
        print(f"No early '{package_prefix}' imports found before 'class {target_class}' in {path}.")
        return

    lines = source.splitlines(keepends=True)
    moved_texts = [
        "".join(lines[start - 1:end]) for start, end in movable_ranges
    ]

    lines_to_remove = {
        i for start, end in movable_ranges for i in range(start - 1, end)
    }
    remaining_lines = [
        line for i, line in enumerate(lines) if i not in lines_to_remove
    ]

    if remaining_lines and not remaining_lines[-1].endswith("\n"):
        remaining_lines[-1] += "\n"

    remaining_lines.append("\n")
    remaining_lines.extend(moved_texts)

    path.write_text("".join(remaining_lines))
    print(f"Moved {len(movable_ranges)} early '{package_prefix}' import(s) to the end of {path}:")
    for text in moved_texts:
        print(f"  {text.strip()}")


if __name__ == "__main__":
    main()
