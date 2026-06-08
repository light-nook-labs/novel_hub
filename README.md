# Novel Hub

## Database ER Diagram

```mermaid
erDiagram
    Author {
        CharField name UK "unique"
    }

    Tag {
        CharField name UK "unique"
    }

    Contest {
        CharField name UK "unique"
    }

    Novel {
        CharField title
        SmallIntegerField ptype INDEX
        SmallIntegerField genre INDEX
        SmallIntegerField status INDEX
        IntegerField click_num
        IntegerField word_num
        IntegerField praise_num
        IntegerField like_num
        BooleanField has_banner INDEX
        IntegerField review_num
        IntegerField comment_num
        URLField cover
        DateTimeField last_update
        DateTimeField db_update "auto_now"
    }

    Author ||--o{ Novel : "1:N"
    Contest ||--o{ Novel : "1:N"
    Novel }o--o{ Tag : "M2M"
```

### Relationships
1. Author  : Novel  →  One-to-Many (`ForeignKey`, `on_delete=SET NULL`)
2. Contest : Novel  →  One-to-Many (`ForeignKey`, `on_delete=SET NULL`)
3. Novel   : Tag    →  Many-to-Many (`ManyToManyField`)

### Mappings (Context Processor)

Enum fields `ptype`, `genre`, `status` store integer values mapped via `Mapping` class:

| Field   | Values (en → zh)                              |
|---------|-----------------------------------------------|
| genre   | magic→魔幻, eastern→玄幻, ancient→古风, sci_fi→科幻, school→校园, urban→都市, game→游戏, doujin→同人, mystery→悬疑 |
| status  | finished→已完结, on_going→连载中, died→断更    |
| ptype   | free→免费, sign→签约, vip→VIP                 |

Unknown values fall back to `OTHER` (index 1).
