# Web Search MCP for Architect Mode (Relaxed)

## Rule

When in **Architect Mode**:

- **Use web search selectively**:
  - ✅ Perform a web search if the request involves **current best practices, external libraries, vendor comparisons, or recent standards**.
  - ✅ Search if the topic covers **technologies that evolve quickly** (e.g. cloud services, DevOps tools, framework versions, SaaS pricing).
  - ❌ Skip search if the request is **self-contained** or relies on well-established knowledge (e.g. known design patterns, language features, common project structures).

- **If a search is used**:
  - Summarize findings clearly and cite sources.
  - Integrate external information into your architectural reasoning before providing the final recommendation.

- **If search is skipped**:
  - Briefly state that search wasn’t necessary because the request is self-contained or based on established knowledge.

---

## Examples

### Should search
- “Which cloud provider has the cheapest managed Postgres in 2025?”
- “Best practices for deploying FastAPI on AWS ECS this year?”
- “Compare Qdrant vs Weaviate vs Pinecone latest versions.”

### Don’t need search
- “Refactor this project structure to follow clean architecture.”
- “Show me a FastAPI middleware example for logging.”
- “Explain pros/cons of monorepo vs polyrepo in a small startup.”

---
