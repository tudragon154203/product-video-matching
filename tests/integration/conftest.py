"""
Integration tests bootstrap:
- Path setup for shared libs and support modules
- Environment overrides to enforce real service usage (no mocks)
- Infra auto-start via Docker Compose (no build) when both Postgres and RabbitMQ are down
- Central config reload to apply overrides
- Enforcement checks to validate live-service configuration
- Import root tests/conftest fixtures into this collection root
"""

from support.utils.media_manager import ensure_test_media_available
from support.utils.service_enforcement import enforce_real_service_usage
from support.environment.infra_bootstrap import ensure_infra_running
import importlib.util
from pathlib import Path
import sys
import os
import importlib

# Set up paths first before importing support modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Minimal dotenv loader: load tests/.env.test without overriding existing os.environ


def load_env_file():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(base_dir, ".env.test")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v


# Pre-load env before any other imports/enforcement
load_env_file()


# Import media_manager from parent tests directory
sys.path.insert(0, str(Path(__file__).parent.parent / 'support'))

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

# Now import support modules after path setup is complete

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

# Ensure test media files are available (auto-copy from tests/mock_data if needed)
if not ensure_test_media_available(WORKSPACE_ROOT):
    print("WARNING: Failed to ensure test media files are available")

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

# Import feature extraction fixtures
fixtures_path = TESTS_DIR / "support" / "fixtures" / "feature_extraction_fixtures.py"
spec = importlib.util.spec_from_file_location("feature_extraction_fixtures", str(fixtures_path))
fixtures_module = importlib.util.module_from_spec(spec)
sys.modules["feature_extraction_fixtures"] = fixtures_module
spec.loader.exec_module(fixtures_module)

# Export fixtures from the fixtures module
for name in dir(fixtures_module):
    if not name.startswith("_") and hasattr(fixtures_module, name):
        attr = getattr(fixtures_module, name)
        if hasattr(attr, "_pytestfixturefunction") or (hasattr(attr, "__pytest_wrapped__") and hasattr(attr.__pytest_wrapped__, "obj")):
            globals()[name] = attr
