---
name: Style baselines observed
description: Patterns observed from models.py and enums.py that serve as the codebase style reference
type: reference
---

When reviewing code for style compliance, use these observations as the "target style":

**models.py patterns:**
- `from sqlalchemy import UniqueConstraint` at top with other third-party imports
- `from sqlmodel import Field, Relationship, SQLModel` — sorted A-Z within single-module imports
- `__table_args__` on SQLModel subclasses for DB-level constraints
- Module-level comment blocks use `####` style (e.g., `####################`, `#########`)
- Fields use `int | None = None` for nullable columns that aren't primary keys
- Foreign keys: `int | None = Field(default=None, foreign_key="...", ondelete="SET NULL")`
- Relationships: `list[Banner] = Relationship(...)` for one-to-many, `Optional["Novel"] | None` for nullable back-refs (pre-existing old style)

**enums.py patterns:**
- Top-level class docstrings are single-line, e.g., `"""小说分类枚举。"""`
- Module-level comment for aliases: `# alias`
- One blank line between classes
- Private _mapping assignments after each class definition

**Import ordering (verified):**
- standard lib → third-party → local, one blank line between groups
- Within third-party: `pandas` before `sqlalchemy` before `sqlmodel`
- Within same module: sorted A-Z by imported name
- Aliased imports sorted by original name (e.g., `insert as sa_insert` sorted under `i`)
