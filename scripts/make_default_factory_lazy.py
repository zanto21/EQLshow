#!/usr/bin/env python3
"""
Replace an eager `field(default_factory=ClassName)` with a lazy lambda.

Background:
graph_node.py's `class NodeArtifacts` has a dataclass field
`constraints: ConstraintCollection = field(default_factory=ConstraintCollection)`.
Passing the class itself as `default_factory` requires the name
`ConstraintCollection` to already be bound in graph_node.py's namespace at
the moment the class body executes, i.e. eagerly, at import time.

ConstraintCollection's own module, however, transitively needs
MotionStatechartNode back from graph_node.py (through
motion_statechart.exceptions), which is not defined yet at that point in
graph_node.py's own loading. This is a genuine, structural circular
dependency: ConstraintCollection is needed early (for the field default),
but can only be fully loaded late (after MotionStatechartNode exists).

The fix: wrap the default factory in a lambda, so the reference to
ConstraintCollection is only evaluated the first time a NodeArtifacts
instance is actually created (at runtime, long after all modules have
finished loading), rather than at class-definition time. This means the
import of ConstraintCollection no longer needs to happen early at all, and
can safely be moved to the end of the file (with a separate tool), fully
breaking the cycle.

Usage:
    python3 make_default_factory_lazy.py <path_to_file.py> <ClassName>
"""

import sys
from pathlib import Path

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 make_default_factory_lazy.py <path_to_file.py> <ClassName>")
        sys.exit(1)

    path = Path(sys.argv[1])
    class_name = sys.argv[2]

    old_text = f"field(default_factory={class_name})"
    new_text = f"field(default_factory=lambda: {class_name}())"

    content = path.read_text()
    count = content.count(old_text)

    if count == 0:
        print(f"'{old_text}' not found in {path}; nothing to do.")
        sys.exit(1)

    content = content.replace(old_text, new_text)
    path.write_text(content)
    print(f"Replaced {count} occurrence(s) of '{old_text}' with '{new_text}' in {path}.")


if __name__ == "__main__":
    main()
