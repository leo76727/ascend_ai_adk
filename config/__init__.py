# Mark this directory as a Python package so "import config" works when
# the repository root is present on PYTHONPATH or when running from the
# project root.

# Optionally re-export the config module object for convenience.
from . import config as config  # noqa: F401
