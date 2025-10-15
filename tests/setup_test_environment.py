#!/usr/bin/env python3
"""
Setup script for Collection Phase Test Environment

This script configures the test environment, installs pre-commit hooks,
and validates that everything is ready for test execution.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse

def run_command(cmd, description, check=True, capture_output=True):
    """Run a command with error handling."""
    print(f"🔄 {description}")
    print(f"   Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        if result.stdout and capture_output:
            print(f"   Output: {result.stdout.strip()}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e.stderr if e.stderr else 'Command failed'}")
        return False, e.stderr if e.stderr else ""

def setup_pre_commit_hooks():
    """Setup pre-commit hooks for test validation."""
    print("\n🔧 Setting up pre-commit hooks...")
    
    # Make the pre-commit hook executable
    hook_path = Path(".githooks/pre-commit-test-validation.sh")
    if hook_path.exists():
        os.chmod(hook_path, 0o755)
        print("   ✅ Made pre-commit hook executable")
    else:
        print("   ❌ Pre-commit hook not found")
        return False
    
    # Setup git hooks directory
    git_hooks_dir = Path(".git/hooks")
    if git_hooks_dir.exists():
        pre_commit_link = git_hooks_dir / "pre-commit"
        
        # Remove existing pre-commit hook
        if pre_commit_link.exists():
            pre_commit_link.unlink()
            print("   🗑️  Removed existing pre-commit hook")
        
        # Create symlink to our hook
        try:
            pre_commit_link.symlink_to("../../.githooks/pre-commit-test-validation.sh")
            print("   ✅ Created symlink for pre-commit hook")
        except OSError:
            # Fallback: copy the file
            shutil.copy(hook_path, pre_commit_link)
            os.chmod(pre_commit_link, 0o755)
            print("   ✅ Copied pre-commit hook (symlink failed)")
    else:
        print("   ⚠️  .git/hooks directory not found (not a git repository)")
    
    return True

def validate_python_environment():
    """Validate Python environment and dependencies."""
    print("\n🐍 Validating Python environment...")
    
    # Check Python version
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"   ❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    print(f"   ✅ Python version: {version.major}.{version.minor}.{version.micro}")
    
    # Check required packages
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-xdist",
        "pytest-timeout",
        "pytest-cov",
        "asyncpg",
        "aio-pika",
        "httpx"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"   ❌ {package} missing")
    
    if missing_packages:
        print(f"\n   💡 Install missing packages: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def validate_project_structure():
    """Validate project structure and required files."""
    print("\n📁 Validating project structure...")
    
    required_files = [
        "pytest.ini",
        "requirements-test.txt",
        "tests/conftest.py",
        "tests/integration/test_collection_phase_happy_path.py",
        "tests/integration/test_collection_phase_integration.py",
        "tests/integration/test_observability_validation.py",
        "tests/run_collection_phase_tests.py",
        "infra/pvm/docker-compose.dev.cpu.yml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"   ❌ {file_path}")
    
    if missing_files:
        print(f"\n   ❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    return True

def validate_test_utilities():
    """Validate test utilities can be imported."""
    print("\n🧪 Validating test utilities...")
    
    utilities = [
        ("tests.utils.message_spy", "CollectionPhaseSpy"),
        ("tests.utils.db_cleanup", "CollectionPhaseCleanup"),
        ("tests.utils.event_publisher", "TestEventFactory"),
        ("tests.utils.test_environment", "CollectionPhaseTestEnvironment"),
        ("tests.utils.observability_validator", "ObservabilityValidator")
    ]
    
    for module, class_name in utilities:
        try:
            sys.path.insert(0, "tests")
            __import__(module)
            print(f"   ✅ {module}.{class_name}")
        except ImportError as e:
            print(f"   ❌ {module}.{class_name}: {e}")
            return False
        finally:
            if "tests" in sys.path:
                sys.path.remove("tests")
    
    return True

def validate_pytest_configuration():
    """Validate pytest configuration."""
    print("\n⚙️  Validating pytest configuration...")
    
    # Check pytest.ini
    if not Path("pytest.ini").exists():
        print("   ❌ pytest.ini not found")
        return False
    
    # Try to parse pytest.ini
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read("pytest.ini")
        
        if "pytest" not in config:
            print("   ❌ pytest.ini missing [pytest] section")
            return False
        
        # Check required settings
        required_settings = ["asyncio_mode", "addopts", "markers"]
        for setting in required_settings:
            if setting not in config["pytest"]:
                print(f"   ❌ pytest.ini missing '{setting}' setting")
                return False
        
        print("   ✅ pytest.ini configuration valid")
        
    except Exception as e:
        print(f"   ❌ pytest.ini parsing error: {e}")
        return False
    
    # Test pytest collection
    success, output = run_command(
        ["python", "-m", "pytest", "--collect-only", "-q", "tests/integration/"],
        "Testing pytest collection",
        check=False
    )
    
    if not success:
        print("   ❌ pytest collection failed")
        print(f"   Output: {output}")
        return False
    
    print("   ✅ pytest collection successful")
    return True

def setup_environment_files():
    """Setup environment files if needed."""
    print("\n📝 Setting up environment files...")
    
    # Check if .env file exists
    env_file = Path("infra/pvm/.env")
    env_example = Path("infra/pvm/.env.example")
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("   ✅ Created .env from .env.example")
        print("   💡 Please review and update .env with your configuration")
    elif env_file.exists():
        print("   ✅ .env file exists")
    else:
        print("   ⚠️  No .env or .env.example found")
    
    return True

def create_directories():
    """Create necessary directories."""
    print("\n📂 Creating directories...")
    
    directories = [
        "data/postgres_data",
        "data/rabbitmq_data",
        "data/redis_data",
        "model_cache",
        "logs",
        "test_reports"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    return True

def run_validation_tests():
    """Run a quick validation test to ensure everything works."""
    print("\n🧪 Running validation tests...")
    
    # Test basic pytest functionality
    success, output = run_command(
        ["python", "-m", "pytest", "--version"],
        "Checking pytest version",
        check=False
    )
    
    if not success:
        print("   ❌ pytest not working")
        return False
    
    # Test test collection
    success, output = run_command(
        ["python", "-m", "pytest", "--collect-only", "-q", "tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset"],
        "Testing specific test collection",
        check=False
    )
    
    if not success:
        print("   ❌ Test collection failed")
        return False
    
    print("   ✅ Validation tests passed")
    return True

def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Setup Collection Phase Test Environment")
    parser.add_argument("--skip-hooks", action="store_true", help="Skip pre-commit hooks setup")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("🚀 Setting up Collection Phase Test Environment")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pytest.ini").exists():
        print("❌ Error: pytest.ini not found. Please run from project root.")
        sys.exit(1)
    
    setup_steps = [
        ("Python Environment", validate_python_environment),
        ("Project Structure", validate_project_structure),
        ("Environment Files", setup_environment_files),
        ("Directories", create_directories),
        ("Test Utilities", validate_test_utilities),
        ("Pytest Configuration", validate_pytest_configuration),
    ]
    
    if not args.skip_hooks:
        setup_steps.insert(0, ("Pre-commit Hooks", setup_pre_commit_hooks))
    
    failed_steps = []
    
    for step_name, step_func in setup_steps:
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"   ❌ {step_name} failed with exception: {e}")
            failed_steps.append(step_name)
    
    if not args.skip_validation:
        if not run_validation_tests():
            failed_steps.append("Validation Tests")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary")
    print("=" * 50)
    
    if failed_steps:
        print(f"❌ {len(failed_steps)} setup step(s) failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\n💡 Please fix the issues above before running tests")
        sys.exit(1)
    else:
        print("✅ All setup steps completed successfully!")
        print("\n🎉 Test environment is ready!")
        print("\n📋 Next steps:")
        print("   1. Start the development stack:")
        print("      docker compose -f infra/pvm/docker-compose.dev.cpu.yml up -d")
        print("   2. Run migrations:")
        print("      python scripts/run_migrations.py upgrade")
        print("   3. Run tests:")
        print("      python tests/run_collection_phase_tests.py")
        print("\n📖 For more information, see: docs/TEST_EXECUTION_GUIDE.md")

if __name__ == "__main__":
    main()