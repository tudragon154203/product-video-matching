# Windows Command Prompt Compatibility Rules

When generating commands intended for **Windows Command Prompt (cmd.exe):**

## 🚫 Do Not
- ❌ Do NOT use `&` or `&&` to chain commands.  
  - Always split them into **separate lines** instead.

- ❌ Do NOT use Linux/Unix-only commands such as:
  - `grep`, `cat`, `ls`, `pwd`, `touch`, `rm`, `mv`, `chmod`, etc.  
  - These are not available in Windows Command Prompt by default.

## ✅ Do
- Provide **Windows-native equivalents** or commands instead:
  - Use `findstr` instead of `grep`.  
  - Use `dir` instead of `ls`.  
  - Use `cd` (already works the same).  
  - Use `copy` instead of `cp`.  
  - Use `del` instead of `rm`.  
  - Use `move` instead of `mv`.  

- For chaining, write commands separately:
  ```cmd
  cd services\dropship-product-finder
  python -m pytest tests\ -v
  ```

- If the user explicitly asks for **PowerShell** or **Linux/macOS shell**, then normal commands (e.g., `grep`, `ls`, `&&`, `;`) are fine.  
- But **for Windows Command Prompt examples, always stick to Windows-native commands**.

---

**Scope:** All Modes (Code, Debug, Ask, Architect, Orchestrator)  
**Priority:** HIGH
