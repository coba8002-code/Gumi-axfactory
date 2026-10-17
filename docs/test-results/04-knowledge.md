# Stage 4 — approved evidence retrieval

- Literal wildcard escaping unit test passes locally.
- Added PostgreSQL tests for unapproved/cross-factory exclusion and source citation; CI required.
- Explicit retrieval-only PoC: no external model key was configured, no embedding/LLM service
  is claimed or silently substituted. API gives approved actions/outcomes with incident citations.
- Human approval is mandatory; worker notes never become verified knowledge automatically.
- DeepSeek Harness remains outside production dependencies pending separate pinned security review.
