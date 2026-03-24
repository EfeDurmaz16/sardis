-- Migration 049: Placeholder
-- This migration was skipped during development. This placeholder ensures
-- sequential migration numbering remains intact (048 -> 049 -> 050).

INSERT INTO schema_migrations (version, description, applied_at)
VALUES (49, 'placeholder', NOW())
ON CONFLICT (version) DO NOTHING;
