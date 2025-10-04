"""Test configuration helpers for dropship-product-finder unit tests."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

# Ensure the hyphenated service directory can be imported as services.dropship_product_finder
SERVICE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "services.dropship_product_finder"

if PACKAGE_NAME not in sys.modules:
    spec = importlib.util.spec_from_loader(PACKAGE_NAME, loader=None, is_package=True)
    module = importlib.util.module_from_spec(spec)
    module.__path__ = [str(SERVICE_DIR)]  # allow subpackages/modules inside the service
    sys.modules[PACKAGE_NAME] = module

    # Make the compatibility module discoverable when iterating over packages
    if getattr(module, "__spec__", None) is None:
        module.__spec__ = importlib.machinery.ModuleSpec(
            name=PACKAGE_NAME,
            loader=None,
            is_package=True,
        )
        module.__spec__.submodule_search_locations = module.__path__
