"""Import-path bootstrap for the reorganized repo.

The experiment scripts live in experiments/<group>/ and archive/ but still use
flat ``import <module>`` statements and cross-import each other (e.g.
axiom_tests -> structural_novelty_run, novelty_decay -> measure_diversity).
Importing this module adds the repo root and every experiment folder to
``sys.path`` so those flat imports keep resolving no matter which folder a
module lives in.

Entry scripts import it via the 3-line header::

    import os, sys
    sys.path.insert(0, os.getcwd())   # repo root (run scripts from repo root)
    import _exppath  # noqa: E402  (extends sys.path to experiment folders)

Run scripts from the repo root so the CWD-relative ``results/`` paths resolve.
"""

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent

_dirs = [_ROOT, _ROOT / "experiments", _ROOT / "archive", _ROOT / "figures"]
_dirs += [p for p in (_ROOT / "experiments").glob("*") if p.is_dir()]

for _d in _dirs:
    _s = str(_d)
    if _d.exists() and _s not in sys.path:
        sys.path.insert(0, _s)
