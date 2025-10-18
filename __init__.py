"""Index Generator Package"""

# Lazy import to avoid circular dependency and module loading issues
# The kbi.py script is designed to run standalone, but we need to support
# "from kbi import KnowledgebaseIndexer" for tests

def __getattr__(name):
    """Lazy import of KnowledgebaseIndexer."""
    if name == 'KnowledgebaseIndexer':
        # Import locally to get the class
        import sys
        import os
        import importlib.util

        # Get the path to kbi.py
        pkg_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(pkg_dir)
        kbi_py_path = os.path.join(pkg_dir, 'kbi.py')

        # Ensure parent and package dirs are in path for imports
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        if pkg_dir not in sys.path:
            sys.path.insert(0, pkg_dir)

        # Load kbi.py as a module with a different name to avoid conflict
        spec = importlib.util.spec_from_file_location("_kbi_main_module", kbi_py_path)
        kbi_module = importlib.util.module_from_spec(spec)

        # Add to sys.modules to cache it
        sys.modules['_kbi_main_module'] = kbi_module
        spec.loader.exec_module(kbi_module)

        return kbi_module.KnowledgebaseIndexer

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['KnowledgebaseIndexer']