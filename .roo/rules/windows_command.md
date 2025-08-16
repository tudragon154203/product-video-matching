# Windows Command Prompt Rule: No & or &&

- When generating commands for **Windows Command Prompt** (cmd.exe):
  - **Do NOT use `&` or `&&`** to chain commands.
  - Instead, write them as **two (or more) separate commands**, each on its own line.

❌ Example (invalid in Windows cmd):
cd services/dropship-product-finder && python -m pytest tests/

✅ Correct Example (Windows cmd):
cd services/dropship-product-finder
python -m pytest tests/ -v