---
name: Comment separator style
description: The project uses #-based block comment separators whose hash count matches the enclosed text width
type: project
---

All section-separator comment blocks (e.g., `########## / # SQLite # / ##########`) use ASCII `#` characters whose count matches the character width of the enclosed label. This pattern is established in `models.py` and followed in `engine.py`. New separator blocks should follow this same alignment convention.

**Files using this pattern:**
- `database/models.py` — separators at lines 6, 16, 53
- `database/engine.py` — separators at lines 8, 24
