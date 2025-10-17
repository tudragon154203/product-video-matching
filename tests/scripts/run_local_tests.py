#!/usr/bin/env python3
"""
Local Test Runner for Collection Phase Integration Tests

Simple script to run collection phase tests locally with proper setup and cleanup.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TESTS_DIR.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"


def build_env():
    """Return environment with PYTHONPATH pointing at shared libs."""
    env = os.environ.copy()
    paths = [str(COMMON_PY_DIR), str(LIBS_DIR), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join([p for p in paths if p])
    return env


def run_command(cmd, description, timeout=300):
    """Run a command with error handling."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_env(),
        )

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False

    return True


def main():
    """Main function to run local tests."""
    parser = argparse.ArgumentParser(description="Run collection phase tests locally")
    parser.add_argument("--test-type", choices=["collection", "integration", "observability", "all"],
                        default="collection", help="Type of tests to run")
    parser.add_argument("--skip-setup", action="store_true", help="Skip environment setup")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🚀 Starting Local Collection Phase Test Runner")
    print("=" * 50)

    # Ensure we are running from the project root
    os.chdir(PROJECT_ROOT)

    runner_script = TESTS_DIR / "scripts" / "run_collection_phase_tests.py"
    if not runner_script.exists():
        print(f"❌ Could not find test runner helper at {runner_script.relative_to(PROJECT_ROOT)}")
        sys.exit(1)

    # Environment setup
    if not args.skip_setup:
        print("\n📋 Setting up test environment...")

        # Check if Docker Compose is running
        if not run_command(
            ["docker", "compose", "-f", "infra/pvm/docker-compose.dev.cpu.yml", "ps"],
            "Checking Docker Compose status",
            timeout=30
        ):
            print("❌ Docker Compose is not running. Please start it first:")
            print("   docker compose -f infra/pvm/docker-compose.dev.cpu.yml up -d")
            sys.exit(1)

        # Run migrations
        if not run_command(
            ["python", "scripts/run_migrations.py", "upgrade"],
            "Running database migrations",
            timeout=60
        ):
            print("❌ Database migration failed")
            sys.exit(1)

        print("✅ Environment setup complete")

    # Run tests based on type
    test_commands = []

    if args.test_type in ["collection", "all"]:
        test_commands.extend([
            (["python", "-m", "pytest", "tests/integration/test_collection_phase_"
             "happy_path.py::TestCollectionPhaseHappyPath::test_collection_"
              "phase_happy_path_minimal_dataset", "-v"],
             "Collection Phase Happy Path Minimal Dataset"),
            (["python", "-m", "pytest", "tests/integration/test_collection_phase_"
              "happy_path.py::TestCollectionPhaseHappyPath::test_collection_"
              "phase_idempotency_validation", "-v"],
             "Collection Phase Idempotency Validation")
        ])

    if args.test_type in ["integration", "all"]:
        test_commands.extend([
            (["python", "-m", "pytest", "tests/integration/test_collection_phase_"
              "integration.py::TestCollectionPhaseIntegration::test_complete_"
              "collection_workflow", "-v"],
             "Complete Collection Workflow"),
            (["python", "-m", "pytest", "tests/integration/test_collection_phase_"
              "integration.py::TestCollectionPhaseIntegration::test_concurrent_"
              "collection_workflows", "-v"],
             "Concurrent Collection Workflows")
        ])

    if args.test_type in ["observability", "all"]:
        test_commands.extend([
            (["python", "-m", "pytest", "tests/integration/test_observability_"
              "validation.py::TestObservabilityValidator::test_observability_"
              "validator_initialization", "-v"],
             "Observability Validator Initialization"),
            (["python", "-m", "pytest", "tests/integration/test_observability_"
              "validation.py::TestObservabilityIntegration::test_full_"
              "observability_workflow", "-v"],
             "Full Observability Workflow")
        ])

    # Execute tests
    failed_tests = []

    for cmd, description in test_commands:
        if args.verbose:
            cmd.extend(["-s", "--tb=long"])

        if not run_command(cmd, description, timeout=600):
            failed_tests.append(description)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    if failed_tests:
        print(f"❌ {len(failed_tests)} test(s) failed:")
        for test in failed_tests:
            print(f"   - {test}")
        print("\n💡 Check the logs above for details")
        sys.exit(1)
    else:
        print("✅ All tests passed successfully!")
        print("\n🎉 Collection phase integration tests are working correctly!")

    # Cleanup instructions
    if not args.skip_setup:
        print("\n🧹 Cleanup suggestions:")
        print("   - Test data is automatically cleaned up")
        print("   - Docker Compose stack can be left running for future tests")
        print("   - To stop: docker compose -f infra/pvm/docker-compose.dev.cpu.yml down")


if __name__ == "__main__":
    main()
