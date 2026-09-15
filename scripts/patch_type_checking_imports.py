#!/usr/bin/env python3
"""
Promote TYPE_CHECKING-only imports to unconditional imports.

Background:
giskardpy (and potentially other packages in this monorepo) uses the common
Python pattern of importing classes only inside `if TYPE_CHECKING:` blocks to
avoid circular imports at runtime. Type checkers like mypy resolve these
imports statically, but krrood's runtime ORM generation needs the actual
classes to be importable when it inspects type annotations. Without this
patch, ORM generation fails with `CouldNotResolveType` for every class that
is only imported under TYPE_CHECKING.

This script finds every `if TYPE_CHECKING:` block in all .py files under a
given package directory, and duplicates its import statements as unconditional
imports placed directly above the `if TYPE_CHECKING:` line. It uses the `ast`
module (not regex) so that multi-line parenthesized imports such as

    if TYPE_CHECKING:
        from foo.bar import (
            A,
            B,
        )

are handled correctly. Only the indentation of each import statement's first
line is adjusted to match the indentation of the `if TYPE_CHECKING:` line
itself; continuation lines inside parentheses are left untouched, since their
leading whitespace does not affect how Python parses them.

Usage:
    python3 patch_type_checking_imports.py <package_root_directory>
"""

import ast
import sys
from pathlib import Path


def find_type_checking_blocks(source: str) -> list[tuple[int, int, list[tuple[int, int]]]]:
    """
    Find every `if TYPE_CHECKING:` block in the source and the import
    statements directly inside it.

    :param source: The full source code of a Python file
    :return: List of (if_lineno, if_col_offset, import_ranges) tuples, where
        import_ranges is a list of (start_line, end_line) for each import
        statement found directly in that block's body. Line numbers are
        1-indexed and inclusive, matching Python's ast module.
    """
    tree = ast.parse(source)
    blocks: list[tuple[int, int, list[tuple[int, int]]]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        test = node.test
        is_type_checking = (
            (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        )
        if not is_type_checking:
            continue

        import_ranges = [
            (statement.lineno, statement.end_lineno)
            for statement in node.body
            if isinstance(statement, (ast.Import, ast.ImportFrom))
        ]
        if import_ranges:
            blocks.append((node.lineno, node.col_offset, import_ranges))

    return blocks


def reindent_first_line(statement_text: str, target_indent: int) -> str:
    """
    Replace the leading whitespace of the first line of an import statement
    with `target_indent` spaces. Continuation lines (inside parentheses or
    after a backslash) are left unchanged, since Python does not require any
    particular indentation for them.

    :param statement_text: The full source text of one import statement,
        possibly spanning multiple lines
    :param target_indent: Number of spaces the first line should be
        indented with
    :return: The statement text with only its first line's indentation fixed
    """
    lines = statement_text.splitlines(keepends=True)
    first_line = lines[0]
    stripped = first_line.lstrip(" ")
    lines[0] = (" " * target_indent) + stripped
    return "".join(lines)


def patch_file(path: Path) -> bool:
    """
    Patch a single file in place, promoting its TYPE_CHECKING-only imports
    to unconditional imports at the same indentation level as the
    `if TYPE_CHECKING:` statement itself. Does nothing if the file has no
    such imports.

    :param path: Path to the Python file to patch
    :return: True if the file was modified, False otherwise
    """
    source = path.read_text()

    try:
        blocks = find_type_checking_blocks(source)
    except SyntaxError:
        # A handful of files may not parse cleanly on their own; skip them.
        return False

    if not blocks:
        return False

    lines = source.splitlines(keepends=True)

    # Apply insertions from bottom to top so that earlier line numbers in
    # the file remain valid while later ones are being modified.
    for if_lineno, if_col_offset, import_ranges in sorted(blocks, reverse=True):
        import_blocks = [
            reindent_first_line("".join(lines[start - 1:end]), if_col_offset)
            for start, end in import_ranges
        ]
        insertion_text = "".join(import_blocks)
        insertion_index = if_lineno - 1
        lines = lines[:insertion_index] + [insertion_text] + lines[insertion_index:]

    path.write_text("".join(lines))
    return True


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 patch_type_checking_imports.py <package_root_directory>")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    patched_files = []
    for path in root.rglob("*.py"):
        if patch_file(path):
            patched_files.append(path)

    print(f"Patched {len(patched_files)} file(s):")
    for path in patched_files:
        print(f"  {path}")


if __name__ == "__main__":
    main()
