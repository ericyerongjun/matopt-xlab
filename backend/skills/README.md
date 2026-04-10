# SKILL.md Store

This directory is the managed storage for skill documents used by the agentic backend.

## Layout

- One folder per skill slug
- Each folder contains a single `SKILL.md`

Example:

```text
backend/skills/
  graph-visualizer/
    SKILL.md
  data-storytelling/
    SKILL.md
```

## API Management

The backend now exposes skill management endpoints:

- `GET /api/skills`
- `GET /api/skills/{slug}`
- `POST /api/skills` (create or update)
- `DELETE /api/skills/{slug}`

Skills can also be surfaced to the LangGraph agent through `skill_slugs` in the chat payload.
