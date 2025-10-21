#!/usr/bin/env python3
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"
INTEGRATION_DIR = TESTS_DIR / "integration"

for p in (TESTS_DIR, INTEGRATION_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)

# Import and test the class
from support.feature_extraction_spy import FeatureExtractionSpy

# Check if method exists
spy = FeatureExtractionSpy('amqp://guest:guest@localhost:5672//')
print("Available methods:")
for attr in dir(spy):
    if 'wait_for' in attr:
        print(f"  {attr}")

print(f"Has wait_for_products_image_masked: {hasattr(spy, 'wait_for_products_image_masked')}")

# Get method if it exists
if hasattr(spy, 'wait_for_products_image_masked'):
    method = getattr(spy, 'wait_for_products_image_masked')
    print(f"Method: {method}")
    print(f"Method callable: {callable(method)}")
