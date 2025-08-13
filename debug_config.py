#!/usr/bin/env python3
import sys
sys.path.append('/app/app')
from config_loader import load_env, parse_env_file
import os

print('=== Debugging config loading ===')
print('Current working directory:', os.getcwd())

# Test the exact same call as in main.py
print('\n=== Testing load_env(".env") ===')
env_path = '.env'
print('Resolved env_path:', env_path)
print('File exists:', os.path.exists(env_path))

if os.path.exists(env_path):
    print('\n=== Parsing file ===')
    kv = parse_env_file(env_path)
    print('OLLAMA_HOST from kv:', kv.get('OLLAMA_HOST'))
    print('kv has', len(kv), 'keys')
    
    print('\n=== Creating config ===')
    config = load_env('.env')
    print('Final ollama_host:', config.ollama_host)
else:
    print('File does not exist!')