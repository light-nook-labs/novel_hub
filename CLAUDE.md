# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Project-Specific Constraints

- **禁止编辑 `meta_spider/` 目录下的任何文件。** 该目录为遗留代码，只读。
- **禁止修改 `output/` 目录下的任何文件。** 该目录为 CI 产出，只读，入库脚本只能从中读取数据。
- **使用 `uv` 管理项目依赖**：所有包管理操作通过 `uv` 执行（`uv add`、`uv sync`、`uv run`），禁止使用 `pip install`。所有库只能安装到虚拟环境（`.venv/`）中。
- **重大更改后更新 README**：每次提交前如有重大更改（新增功能、架构变更、工作流调整），必须同步更新 `README.md` 反映当前状态。
- **Push 前必须审阅代码**：每次 push 之前必须调用 `format-and-comment-reviewer` agent 审阅代码变更，确保格式合规、注释准确。
- **OTHER.txt 是微量数据**：OTHER.txt 记录枚举降级为 OTHER 的异常 nid，总量不超过 20 条。对此文件的任何操作无需考虑性能或内存膨胀问题。

## Coding Style

- **PEP 8 合规**：代码应严格遵循 PEP 8 规范，包括但不限于：
  - 缩进 4 空格，行首无多余空格
  - 运算符两侧空格，逗号后空格，冒号前无空格
  - 每行最大长度 79 字符（docstring/注释 72 字符）
  - 顶层函数和类定义前后各空两行；类内方法定义前后各空一行
- **Black 格式化**：所有 Python 代码必须通过 `uv run black` 格式化后再提交，确保代码风格一致。
- **文档字符串**：遵循 Python 官方推荐写法（PEP 257）。所有公开函数/类使用 `"""` 多行 docstring，第一行为简短摘要，空一行后写详细描述。
- **类型注解**：使用现代语法 `int | None`，不使用 `Optional[int]`。
- **注释**：使用 `#` 行注释解释非显而易见的逻辑，docstring 仅用于函数/类的对外说明。**禁止使用 Unicode box-drawing 字符（如 `──`、`━━`）充当分隔线**，分隔用空行或 `####` 块注释。**禁止使用非 ASCII 字符**（如 `→` 箭头），用 ASCII 替代（如 `->`）。
- **导入顺序**：标准库 → 第三方库 → 本地模块，组间空一行分隔。每组内按首字母顺序（A-Z）排序。
- **Session 方法**：ORM 查询用 `session.exec()`；Core 层 `insert()` / `delete()` 等需使用 `session.execute()`。
- **其他**：以 `models.py` 和 `enums.py` 为编码风格基准，新代码保持前后一致。

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
