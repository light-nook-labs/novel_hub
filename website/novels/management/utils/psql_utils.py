"""PostgreSQL bulk operations utilities.

Optimizations applied (per Supabase Postgres Best Practices):
- COPY for bulk inserts (10-50x faster than INSERT)
- Drop indexes + FK constraints before COPY, rebuild after
- Fast buffer building with direct string concatenation
- Session-level tuning: synchronous_commit=OFF, work_mem
- ANALYZE after bulk loads for fresh statistics
"""

import io

from psycopg2.extras import execute_values

from . import is_na


def insert_simple(cursor, table, columns, rows):
    """INSERT only via COPY. Drops indexes + FK constraints first.

    For tables with FK constraints (e.g. M2M), drops all non-PK indexes
    and FK constraints before COPY, then rebuilds after. This is 20-50x
    faster than COPY with indexes active.
    """
    if not rows:
        return
    clean_rows = _clean_rows(rows)
    cursor.execute(f"TRUNCATE {table} CASCADE")

    # Only drop constraints for large datasets (overhead not worth it for small tables)
    if len(rows) > 10000:
        saved = drop_all_constraints(cursor, table)
        _copy_from(cursor, table, columns, clean_rows)
        rebuild_all_constraints(cursor, table, saved)
    else:
        _copy_from(cursor, table, columns, clean_rows)


def upsert_simple(cursor, table, columns, rows):
    """INSERT ON CONFLICT DO NOTHING via COPY into temp table.

    For large datasets, uses COPY into a temp table then INSERT...ON CONFLICT.
    This is 5-10x faster than execute_values for large datasets.
    """
    if not rows:
        return
    clean_rows = _clean_rows(rows)
    if len(rows) > 10000:
        _upsert_via_temp_table(cursor, table, columns, clean_rows, None)
    else:
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, clean_rows, page_size=10000)


def insert_novels(cursor, columns, rows):
    """INSERT novels via COPY. Drops indexes + FK constraints first."""
    if not rows:
        return
    clean_rows = _clean_rows(rows)
    cursor.execute("TRUNCATE novels_novel CASCADE")
    saved = drop_all_constraints(cursor, "novels_novel")
    _copy_from(cursor, "novels_novel", columns, clean_rows)
    rebuild_all_constraints(cursor, "novels_novel", saved)


def upsert_novels(cursor, columns, rows, update_cols):
    """INSERT ON CONFLICT DO UPDATE via COPY into temp table."""
    if not rows:
        return
    clean_rows = _clean_rows(rows)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    conflict_sql = f"ON CONFLICT (id) DO UPDATE SET {update_set}"
    _upsert_via_temp_table(cursor, "novels_novel", columns, clean_rows, conflict_sql)


def load_maps(cursor):
    """Load author/contest/tag maps from database."""
    cursor.execute("SELECT name, id FROM novels_author")
    author_map = dict(cursor.fetchall())
    cursor.execute("SELECT name, id FROM novels_contest")
    contest_map = dict(cursor.fetchall())
    cursor.execute("SELECT name, id FROM novels_tag")
    tag_map = dict(cursor.fetchall())
    return author_map, contest_map, tag_map


def drop_indexes(cursor, table):
    """Drop non-PK indexes for faster bulk insert."""
    cursor.execute(f"""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = '{table}' AND indexname != '{table}_pkey'
    """)
    saved = cursor.fetchall()
    for idx_name, _ in saved:
        cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
    return saved


def rebuild_indexes(cursor, saved_indexes):
    """Rebuild previously saved indexes."""
    for _, idx_def in saved_indexes:
        cursor.execute(idx_def)


def drop_all_constraints(cursor, table):
    """Drop all non-PK constraints (UNIQUE, FK) for maximum COPY speed.

    Some indexes back UNIQUE constraints and cannot be dropped directly.
    We drop constraints first, then any remaining standalone indexes.

    Returns list of (type, name, definition) for later rebuild.
    """
    saved = []

    # Drop non-PK constraints (UNIQUE and FK only, skip NOT NULL/CHECK)
    cursor.execute(f"""
        SELECT conname, contype, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = '{table}'::regclass
          AND conname != '{table}_pkey'
          AND contype IN ('u', 'f')
    """)
    for con_name, con_type, con_def in cursor.fetchall():
        cursor.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {con_name}")
        saved.append(("constraint", con_name, con_def))

    # Drop any remaining standalone indexes (not backing a constraint)
    cursor.execute(f"""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = '{table}' AND indexname != '{table}_pkey'
    """)
    for idx_name, idx_def in cursor.fetchall():
        cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
        saved.append(("index", idx_name, idx_def))

    return saved


def rebuild_all_constraints(cursor, table, saved):
    """Rebuild previously dropped constraints and indexes."""
    for kind, name, defn in saved:
        if kind == "constraint":
            cursor.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} {defn}")
        else:
            cursor.execute(defn)


def analyze_tables(cursor, tables):
    """Run ANALYZE on specified tables for fresh planner statistics."""
    for table in tables:
        cursor.execute(f"ANALYZE {table}")


def set_session_tuning(cursor, work_mem="256MB", synchronous_commit="OFF"):
    """Set session-level performance parameters for bulk operations.

    - synchronous_commit=OFF: skip fsync per transaction (safe for bulk loads)
    - work_mem: increase for sort/hash operations during bulk load
    - statement_timeout: disable timeout for large COPY operations
    """
    cursor.execute("SET LOCAL statement_timeout = 0")
    cursor.execute(f"SET LOCAL synchronous_commit = {synchronous_commit}")
    cursor.execute(f"SET LOCAL work_mem = '{work_mem}'")


def set_maintenance_tuning(cursor, maintenance_work_mem="512MB"):
    """Set maintenance_work_mem for index rebuilds."""
    cursor.execute(f"SET LOCAL maintenance_work_mem = '{maintenance_work_mem}'")


def disable_triggers(cursor, table):
    """Disable triggers on table for faster bulk insert (use with caution)."""
    cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER ALL")


def enable_triggers(cursor, table):
    """Re-enable triggers on table after bulk insert."""
    cursor.execute(f"ALTER TABLE {table} ENABLE TRIGGER ALL")


# ── Private helpers ─────────────────────────────────────────────────


def _clean_rows(rows):
    """Convert pandas NA to None.

    Uses a fast check: if the value type is a native Python type (not pandas),
    skip the expensive pd.isna() call.
    """
    if not rows:
        return []
    result = []
    for row in rows:
        clean = []
        for v in row:
            if type(v) is int or type(v) is str:
                clean.append(v)
            elif isinstance(v, bool):
                clean.append(int(v))
            elif v is None:
                clean.append(v)
            else:
                clean.append(None if is_na(v) else v)
        result.append(tuple(clean))
    return result


def _copy_from(cursor, table, columns, rows):
    """COPY rows into table using fast buffer construction.

    Escapes backslashes for PostgreSQL COPY protocol.
    """
    if len(columns) == 2:
        lines = [f"{r[0]}\t{r[1]}" for r in rows]
        buf = io.StringIO("\n".join(lines) + "\n")
    else:
        buf = io.StringIO()
        w = buf.write
        for row in rows:
            for i, v in enumerate(row):
                if i > 0:
                    w("\t")
                if v is None:
                    w("\\N")
                else:
                    s = str(v)
                    # Escape backslashes for COPY protocol
                    w(s.replace("\\", "\\\\"))
            w("\n")
    buf.seek(0)
    cursor.copy_from(buf, table, columns=columns, null="\\N", size=65536)


def _upsert_via_temp_table(cursor, table, columns, rows, conflict_sql):
    """Upsert using COPY into a temp table, then INSERT...ON CONFLICT.

    This is 5-10x faster than execute_values for large datasets because
    COPY is much faster than generating VALUES clauses.

    Args:
        table: Target table name
        columns: Column names tuple
        rows: Clean rows to upsert
        conflict_sql: ON CONFLICT clause (e.g. "ON CONFLICT DO NOTHING"
                      or "ON CONFLICT (id) DO UPDATE SET ..."). If None,
                      uses DO NOTHING.
    """
    temp_table = f"_tmp_{table}"
    cols_str = ", ".join(columns)

    # Create temp table with same structure but no constraints
    cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
    cursor.execute(
        f"CREATE TEMP TABLE {temp_table} AS SELECT {cols_str} FROM {table} WHERE false"
    )

    # COPY into temp table (fast)
    _copy_from(cursor, temp_table, columns, rows)

    # Insert from temp table with conflict handling
    if conflict_sql is None:
        conflict_sql = "ON CONFLICT DO NOTHING"
    cursor.execute(
        f"INSERT INTO {table} ({cols_str}) "
        f"SELECT {cols_str} FROM {temp_table} {conflict_sql}"
    )

    # Cleanup
    cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
