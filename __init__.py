"""Index Generator Package"""

# Lazy import to avoid circular dependency and module loading issues
# The kbi.py script is designed to run standalone, but we need to support
# "from kbi import KnowledgebaseIndexer" for tests

def _load_kbi_main():
    """Load kbi.py once (under an alias) and cache it, exposing its symbols."""
    import sys
    import os
    import importlib.util

    if '_kbi_main_module' in sys.modules:
        return sys.modules['_kbi_main_module']

    pkg_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(pkg_dir)
    kbi_py_path = os.path.join(pkg_dir, 'kbi.py')

    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    # Load kbi.py under a distinct name to avoid clashing with this package.
    spec = importlib.util.spec_from_file_location("_kbi_main_module", kbi_py_path)
    kbi_module = importlib.util.module_from_spec(spec)
    sys.modules['_kbi_main_module'] = kbi_module
    spec.loader.exec_module(kbi_module)
    return kbi_module


def __getattr__(name):
    """Lazy passthrough to the public symbols defined in kbi.py."""
    if name in __all__:
        return getattr(_load_kbi_main(), name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ['KnowledgebaseIndexer', 'run_search']