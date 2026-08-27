---
entity_type: project
id: proj_broken
title: Broken YAML (intentional)
status: active
revenue_impact: HIGH
: [unclosed bracket here
xp_points: 99
---

# Broken YAML

Intentionally malformed frontmatter to test error tolerance.
The sync must increment errors=1 but still ingest the other 5 valid notes.