#!/usr/bin/env python3
"""
Prime a target script by replicating giskardpy's own resilient package walk.

Background:
giskardpy's own scripts/generate_orm.py successfully imports the entire
giskardpy package, including modules involved in circular import patterns
(graph_node.py, exceptions.py, context.py, constraint_collection.py, ...).
It does this via `ORMatic.from_package([giskardpy], ...)`, which internally
calls `classes_of_package()`. That function walks every submodule
individually and, crucially, catches and logs any ImportError per submodule
("Module X cannot be parsed") instead of letting it crash the whole script.
This resilient, per-module walk succeeds in loading (and caching in
sys.modules) modules like graph_node.py that a strict, ordinary chain of
`from X import Y` statements cannot, since it tolerates transient circular
import failures on unrelated submodules along the way.

A bare `import giskardpy` does NOT replicate this: it only executes
giskardpy's (likely near-empty) __init__.py and does not recursively import
every submodule, so it provides no priming benefit.

coraplex/scripts/generate_orm.py reaches the same modules through a much
earlier, stricter import chain (via coraplex.exceptions ->
giskardpy.motion_statechart.graph_node directly), which is not
fault-tolerant and crashes immediately on the first circular import it
encounters deeper in the dependency graph.

This script inserts a call to the same `classes_of_package(giskardpy)`
walk as the very first statement of the target script. This forces Python
to fully load and cache as much of the giskardpy package as possible, using
the same resilient order and error tolerance that already works for
giskardpy's own script. By the time coraplex's own (unforgiving) imports
run afterwards, giskardpy.motion_statechart.graph_node (and everything else
the resilient walk managed to load) is already fully present in
sys.modules, so any later `from giskardpy... import ...` statement resolves
instantly without re-triggering module loading.

Usage:
    python3 prime_with_giskardpy_import.py <path_to_script.py>
"""

import sys
from pathlib import Path

PRIME_BLOCK = (
    "# --- priming import, see prime_with_giskardpy_import.py ---\n"
    "import giskardpy as _giskardpy_priming_module\n"
    "from krrood.ormatic.utils import classes_of_package as _classes_of_package_priming\n"
    "_classes_of_package_priming(_giskardpy_priming_module)\n"
    "# --- end priming import ---\n"
)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 prime_with_giskardpy_import.py <path_to_script.py>")
        sys.exit(1)

    path = Path(sys.argv[1])
    content = path.read_text()

    if PRIME_BLOCK in content:
        print(f"{path} already primed; nothing to do.")
        return

    path.write_text(PRIME_BLOCK + content)
    print(f"Prepended the giskardpy priming block to {path}.")


if __name__ == "__main__":
    main()
