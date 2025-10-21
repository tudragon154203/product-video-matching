#!/usr/bin/env python3

import os
import re
import glob

def fix_file_imports(file_path):
    """Fix import issues in a specific file"""
    if not os.path.exists(file_path):
        return False
        
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match the problematic import from tests.integration.support.test_data
    pattern = r'from tests\.integration\.support\.test_data import (\(.*?\)|[^,\n]+(?:,\s*[^,\n]+)*)'
    
    def replacement(match):
        imports_part = match.group(1)
        
        if imports_part.startswith('('):
            imports_part = imports_part[1:-1].strip()  # Remove parentheses
        
        # Create the try/except block
        new_import = f"""# Fix import path - test_data is in integration/support
try:
    from tests.integration.support.test_data import (
{imports_part}
    )
except ImportError:
    # Fallback for when running from different contexts
    from integration.support.test_data import (
{imports_part}
    )"""
        
        return new_import
    
    # Apply the replacement
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed imports in {file_path}")
        return True
    
    return False

# Find all Python test files that might have import issues
test_patterns = [
    'tests/integration/**/*.py',
    'tests/integration/feature_extraction/*.py'
]

files_fixed = 0
for pattern in test_patterns:
    for file_path in glob.glob(pattern, recursive=True):
        if os.path.isfile(file_path) and file_path.endswith('.py'):
            if fix_file_imports(file_path):
                files_fixed += 1

print(f"Fixed imports in {files_fixed} files")
