"""PostgreSQL-specific loader API.

Uses ON CONFLICT DO NOTHING for conflict handling and larger batch sizes.
"""

from django.db.models import F


def bulk_create_ignore(model, objects: list, batch_size: int = 5000) -> int:
    """Bulk create with conflict ignoring for PostgreSQL.

    Args:
        model: Django model class.
        objects: List of model instances.
        batch_size: Number of objects per batch.

    Returns:
        Number of objects created.
    """
    created = model.objects.bulk_create(
        objects,
        batch_size=batch_size,
        ignore_conflicts=True,
    )
    return len(created)


def bulk_create_m2m(through_model, objects: list, batch_size: int = 5000) -> int:
    """Bulk create M2M through table entries for PostgreSQL.

    Args:
        through_model: Django through model class.
        objects: List of through model instances.
        batch_size: Number of objects per batch.

    Returns:
        Number of objects created.
    """
    created = through_model.objects.bulk_create(
        objects,
        batch_size=batch_size,
        ignore_conflicts=True,
    )
    return len(created)


def bulk_upsert(model, objects: list, update_fields: list, batch_size: int = 5000) -> int:
    """Bulk upsert (INSERT ... ON CONFLICT UPDATE) for PostgreSQL.

    Uses raw SQL for performance with ON CONFLICT ... DO UPDATE SET.

    Args:
        model: Django model class.
        objects: List of model instances.
        update_fields: Fields to update on conflict.
        batch_size: Number of objects per batch.

    Returns:
        Number of objects upserted.
    """
    from django.db import connection

    if not objects:
        return 0

    # Get table name
    table_name = model._meta.db_table

    # Get all fields (id + update_fields)
    all_fields = ["id"] + update_fields
    placeholders = ", ".join(["%s"] * len(all_fields))
    columns = ", ".join(all_fields)

    # Build ON CONFLICT UPDATE SET clause
    update_set = ", ".join(
        [f"{f} = EXCLUDED.{f}" for f in update_fields]
    )

    sql = f"""
        INSERT INTO {table_name} ({columns})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {update_set}
    """

    count = 0
    with connection.cursor() as cursor:
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            params_list = []
            for obj in batch:
                params = [getattr(obj, f) for f in all_fields]
                params_list.append(params)
            cursor.executemany(sql, params_list)
            count += len(batch)

    return count
