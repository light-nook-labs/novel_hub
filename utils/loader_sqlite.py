"""SQLite-specific loader API.

Uses INSERT OR IGNORE for conflict handling and batch processing.
"""

from django.db import transaction


def bulk_create_ignore(model, objects: list, batch_size: int = 1000) -> int:
    """Bulk create with conflict ignoring for SQLite.

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


def bulk_create_m2m(through_model, objects: list, batch_size: int = 1000) -> int:
    """Bulk create M2M through table entries for SQLite.

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


def bulk_upsert(model, objects: list, update_fields: list, batch_size: int = 1000) -> int:
    """Bulk upsert for SQLite using transaction.

    Args:
        model: Django model class.
        objects: List of model instances.
        update_fields: Fields to update on conflict.
        batch_size: Number of objects per batch (unused, kept for API consistency).

    Returns:
        Number of objects upserted.
    """
    count = 0
    with transaction.atomic():
        for obj in objects:
            defaults = {f: getattr(obj, f) for f in update_fields}
            model.objects.update_or_create(
                id=obj.id,
                defaults=defaults,
            )
            count += 1
    return count
