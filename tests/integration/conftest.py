"""
Integration tests bootstrap:
- Path setup for shared libs and support modules
- Environment overrides to enforce real service usage (no mocks)
- Infra auto-start via Docker Compose (no build) when both Postgres and RabbitMQ are down
- Central config reload to apply overrides
- Enforcement checks to validate live-service configuration
- Import root tests/conftest fixtures into this collection root
"""

import importlib
import os
import sys
from pathlib import Path
import importlib.util

from support.infra_bootstrap import ensure_infra_running
from support.service_enforcement import enforce_real_service_usage

# Paths
INTEGRATION_DIR = Path(__file__).resolve().parent
TESTS_DIR = INTEGRATION_DIR.parent
WORKSPACE_ROOT = TESTS_DIR.parent
LIBS_DIR = WORKSPACE_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = WORKSPACE_ROOT / "infra"

# Ensure project paths available for imports (support, common_py, config, etc.)
for p in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, WORKSPACE_ROOT, TESTS_DIR, INTEGRATION_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.append(ps)

# Propagate to PYTHONPATH so subprocesses inherit resolution
pythonpath = os.environ.get("PYTHONPATH", "")
paths = [str(COMMON_PY_DIR), str(LIBS_DIR), str(TESTS_DIR), str(WORKSPACE_ROOT)]
merged = os.pathsep.join([p for p in paths + pythonpath.split(os.pathsep) if p])
os.environ["PYTHONPATH"] = merged

# Enforce real services via environment overrides (no mocks allowed in integration tests)
os.environ.update({
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5444",
    "POSTGRES_DB": "product_video_matching",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "dev",
    "VIDEO_CRAWLER_MODE": "live",
    "DROPSHIP_PRODUCT_FINDER_MODE": "live"
})

# Auto-start infra (no build) if core services are down
ensure_infra_running(WORKSPACE_ROOT)

# Reload centralized config after env update
if "config" in sys.modules:
    importlib.reload(sys.modules["config"])
else:
    import config  # type: ignore
    importlib.reload(config)

# Validate real service configuration
enforce_real_service_usage()

# Load root tests/conftest fixtures into this collection root
root_conftest_path = TESTS_DIR / "conftest.py"
spec = importlib.util.spec_from_file_location("root_tests_conftest", str(root_conftest_path))
module = importlib.util.module_from_spec(spec)
sys.modules["root_tests_conftest"] = module
spec.loader.exec_module(module)

for name in dir(module):
    if not name.startswith("_"):
        globals()[name] = getattr(module, name)