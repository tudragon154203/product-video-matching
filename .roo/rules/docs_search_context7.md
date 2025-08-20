# docs_search_context7.md

## Rule: Context7 MCP Usage

### Trigger conditions
Use **Context7 (MCP)** automatically when:
- Query mentions a **specific library/framework/SDK/CLI** (e.g. React, Next.js, Prisma, Supabase, Tailwind, PostgreSQL, MongoDB, Redis, etc.).
- Query specifies a **version** (e.g. “Next.js 14 app router”, “Prisma 5”).
- Query involves **runtime/build errors** that may result from API changes.
- Query requests **official examples / best practices / configs** tied to libraries.

### Do NOT use Context7 when
- Query is pure algorithmic (sorting, DP, Two Sum, etc.).
- Query is about system design principles without libraries.
- Query is non-technical (pricing, company policies).
- Query is opinion/comparison only, unless doc citation is explicitly required.

### How to apply
- Reformulate user query concisely.
- Append:
  ```
  use context7 for <library> [@version]
  ```
- For multiple libraries:
  ```
  use context7 for <lib1> [@version], <lib2> [@version]
  ```

### Answering rules
- Always **cite** official docs from Context7 output.
- Provide **short summary**, then **concise code block**, then **version notes**.
- If Context7 has no match: clearly say so, then fallback to general guidance.

### Token optimization
- Limit answer to **300–500 words** unless asked otherwise.
- Show only essential code snippets.
- Prefer doc links/sections over full copy.

### Pseudo-logic
```
if mentions_library_or_version_or_api_error(user_query):
    activate_context7 = True
else:
    activate_context7 = False
```
