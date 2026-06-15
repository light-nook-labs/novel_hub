# Snapshot System Implementation Plan

## Overview

Track novel metrics over time for trend analysis, with monthly archival to GitHub.

### Storage Budget

```
Single record: 8 (FK) + 4 (date) + 6×4 (metrics) = 36 bytes

ON_GOING (3,003): 3,003 × 36 × 30 = 3.2 MB
Long-term (100): 100 × 36 × 30 = 0.1 MB
Indexes: ~2 MB
─────────────────────────────────────
Total: ~5.3 MB (30 days)
```

---

## 1. Data Models

### 1.1 NovelSnapshot (New)

```python
# website/novels/models.py

class NovelSnapshot(models.Model):
    novel = models.ForeignKey(
        Novel, 
        on_delete=models.CASCADE, 
        related_name='snapshots'
    )
    snapshot_date = models.DateField()
    
    click_num = models.IntegerField(null=True)
    like_num = models.IntegerField(null=True)
    praise_num = models.IntegerField(null=True)
    word_num = models.IntegerField(null=True)
    review_num = models.IntegerField(null=True)
    comment_num = models.IntegerField(null=True)
    
    class Meta:
        unique_together = ('novel', 'snapshot_date')
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['snapshot_date']),
            models.Index(fields=['novel', 'snapshot_date']),
        ]
```

### 1.2 Task (Modify)

```python
# website/novels/models.py

class Task(models.Model):
    class Status(models.TextChoices):
        LONG_TERM = "l", "long_term"  # New
        URGENT = "u", "urgent"
        DEFAULT = "d", "default"
        FINISHED = "f", "finished"
    
    class Meta:
        ordering = [
            models.Case(
                models.When(status="l", then=0),  # Highest priority
                models.When(status="u", then=1),
                models.When(status="d", then=2),
                models.When(status="f", then=3),
            ),
            "-novel_id",
        ]
```

---

## 2. Management Commands

### 2.1 smart_snapshot.py (New)

```python
# website/novels/management/commands/smart_snapshot.py

"""Create daily snapshots of ON_GOING novels and long-term tasks."""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from novels.models import Novel, NovelSnapshot


class Command(BaseCommand):
    help = "Create daily snapshots"
    
    def handle(self, *args, **options):
        today = date.today()
        
        # 1. ON_GOING novels updated within 7 days
        week_ago = today - timedelta(days=7)
        ongoing = Novel.objects.filter(
            status=3,  # ON_GOING
            last_update__date__gte=week_ago
        )
        
        # 2. Long-term tasks
        long_term = Novel.objects.filter(task__status='l')
        
        # 3. Merge and deduplicate
        novels = (ongoing | long_term).distinct()
        
        # 4. Bulk create snapshots
        snapshots = []
        for novel in novels:
            snapshots.append(NovelSnapshot(
                novel=novel,
                snapshot_date=today,
                click_num=novel.click_num,
                like_num=novel.like_num,
                praise_num=novel.praise_num,
                word_num=novel.word_num,
                review_num=novel.review_num,
                comment_num=novel.comment_num,
            ))
        
        created = len(NovelSnapshot.objects.bulk_create(
            snapshots, ignore_conflicts=True
        ))
        
        # 5. Delete snapshots older than 30 days
        cutoff = today - timedelta(days=30)
        deleted, _ = NovelSnapshot.objects.filter(
            snapshot_date__lt=cutoff
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {created}, deleted {deleted}")
        )
```

### 2.2 archive_snapshots.py (New)

```python
# website/novels/management/commands/archive_snapshots.py

"""Archive snapshots to JSONL or CSV files."""

import json
import csv
from datetime import date, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from novels.models import NovelSnapshot


class Command(BaseCommand):
    help = "Archive snapshots to JSONL/CSV"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--month', 
            type=str, 
            help='Month to archive (YYYY-MM format)'
        )
    
    def handle(self, *args, **options):
        # Determine month
        if options['month']:
            year, month = map(int, options['month'].split('-'))
        else:
            last_month = date.today().replace(day=1) - timedelta(days=1)
            year, month = last_month.year, last_month.month
        
        # Get snapshots
        snapshots = NovelSnapshot.objects.filter(
            snapshot_date__year=year,
            snapshot_date__month=month
        ).order_by('novel_id', 'snapshot_date')
        
        count = snapshots.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("No snapshots to archive"))
            return
        
        # Export both formats
        output_dir = Path('release/dataset')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self._export_jsonl(snapshots, year, month, output_dir)
        self._export_csv(snapshots, year, month, output_dir)
        
        # Delete from DB
        deleted, _ = snapshots.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Archived {count} snapshots (JSONL + CSV), deleted {deleted} from DB"
            )
        )
    
    def _export_jsonl(self, snapshots, year, month, output_dir):
        jsonl_dir = output_dir / 'jsonl'
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        output = jsonl_dir / f"snapshot_{year}_{month:02d}.jsonl"
        with open(output, 'w', encoding='utf-8') as f:
            for s in snapshots:
                record = {
                    'nid': s.novel_id,
                    'date': s.snapshot_date.isoformat(),
                    'click_num': s.click_num,
                    'like_num': s.like_num,
                    'praise_num': s.praise_num,
                    'word_num': s.word_num,
                    'review_num': s.review_num,
                    'comment_num': s.comment_num,
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.stdout.write(f"Exported to {output}")
    
    def _export_csv(self, snapshots, year, month, output_dir):
        csv_dir = output_dir / 'csv'
        csv_dir.mkdir(parents=True, exist_ok=True)
        output = csv_dir / f"snapshot_{year}_{month:02d}.csv"
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'nid', 'date', 'click_num', 'like_num', 'praise_num',
                'word_num', 'review_num', 'comment_num'
            ])
            for s in snapshots:
                writer.writerow([
                    s.novel_id, s.snapshot_date, s.click_num, s.like_num,
                    s.praise_num, s.word_num, s.review_num, s.comment_num
                ])
        self.stdout.write(f"Exported to {output}")
```

### 2.3 add_long_term.py (New)

```python
# website/novels/management/commands/add_long_term.py

"""Add novel as long-term task."""

from django.core.management.base import BaseCommand
from novels.models import Novel, Task


class Command(BaseCommand):
    help = "Add novel as long-term task"
    
    def add_arguments(self, parser):
        parser.add_argument('nid', type=int, help='Novel ID')
    
    def handle(self, *args, **options):
        nid = options['nid']
        novel = Novel.objects.get(id=nid)
        
        task, created = Task.objects.update_or_create(
            novel=novel,
            defaults={'status': Task.Status.LONG_TERM}
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} long-term task for {nid}"
            )
        )
```

### 2.4 remove_long_term.py (New)

```python
# website/novels/management/commands/remove_long_term.py

"""Remove novel from long-term tasks."""

from django.core.management.base import BaseCommand
from novels.models import Task


class Command(BaseCommand):
    help = "Remove novel from long-term tasks"
    
    def add_arguments(self, parser):
        parser.add_argument(
            'nid', 
            type=int, 
            nargs='?', 
            help='Novel ID'
        )
        parser.add_argument(
            '--all', 
            action='store_true', 
            help='Remove all long-term tasks'
        )
    
    def handle(self, *args, **options):
        if options['all']:
            deleted, _ = Task.objects.filter(
                status=Task.Status.LONG_TERM
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {deleted} long-term tasks")
            )
        elif options['nid']:
            nid = options['nid']
            deleted, _ = Task.objects.filter(
                novel_id=nid, 
                status=Task.Status.LONG_TERM
            ).delete()
            if deleted:
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted long-term task for {nid}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"No long-term task found for {nid}")
                )
        else:
            self.stdout.write(
                self.style.ERROR("Please provide nid or use --all")
            )
```

### 2.5 run_tasks.py (Modify)

```python
# website/novels/management/commands/run_tasks.py

# Changes:
# 1. Long-term tasks are NOT deleted after processing
# 2. Other tasks are marked as finished and deleted

def handle(self, *args, **options):
    # ... existing logic ...
    
    for task in tasks:
        try:
            # ... crawl and update logic ...
            
            success += 1
            
            # Long-term tasks: keep as-is
            if task.status == Task.Status.LONG_TERM:
                continue
            
            # Others: mark as finished
            task.status = Task.Status.FINISHED
            task.save()
            
        except Exception as e:
            # ... error handling ...
    
    # Delete finished tasks (not long-term)
    deleted, _ = Task.objects.filter(status=Task.Status.FINISHED).delete()
    
    # ... summary output ...
```

---

## 3. Scrapy Integration

### 3.1 SnapshotPipeline (New)

```python
# meta_spider/meta_spider/pipelines.py

"""Snapshot pipeline for creating daily snapshots during crawl."""

from datetime import date
from novels.models import Novel, NovelSnapshot


class SnapshotPipeline:
    """Create snapshot for each ON_GOING novel crawled."""
    
    def process_item(self, item, spider):
        # Only process ON_GOING (sfacg shows as "连载中")
        if item.get('status') != '连载中':
            return item
        
        try:
            novel = Novel.objects.get(id=item['nid'])
            today = date.today()
            
            NovelSnapshot.objects.update_or_create(
                novel=novel,
                snapshot_date=today,
                defaults={
                    'click_num': item.get('click_num'),
                    'like_num': item.get('like_num'),
                    'praise_num': item.get('praise_num'),
                    'word_num': item.get('word_num'),
                    'review_num': item.get('review_num'),
                    'comment_num': item.get('comment_num'),
                }
            )
        except Novel.DoesNotExist:
            spider.logger.warning(f"Novel {item['nid']} not in DB, skipping snapshot")
        
        return item
```

### 3.2 settings.py (Modify)

```python
# meta_spider/meta_spider/settings.py

ITEM_PIPELINES = {
    'meta_spider.pipelines.SnapshotPipeline': 100,
}
```

### 3.3 meta_batch.py (Modify - Add 7-day cutoff)

```python
# meta_spider/meta_spider/spiders/meta_batch.py

from datetime import datetime, timedelta

class MetaBatchSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.should_stop = False
    
    def parse(self, response: HtmlResponse):
        # Stop if reached novels older than 7 days
        if self.should_stop:
            return
        
        items = response.css(".Comic_Pic_List")
        if not items:
            return
        
        for item in items:
            # ... existing parsing logic ...
            yield response.follow(
                novel_url,
                callback=self.parse_detail,
                cb_kwargs={"meta_info": meta_info},
            )
        
        self.curr_page += 1
        if self.curr_page <= self.end_page:
            yield response.follow(self._join_url(), callback=self.parse)
    
    def parse_detail(self, response: HtmlResponse, meta_info: dict[str, Any]):
        # ... existing parsing logic ...
        
        # Check update time for 7-day cutoff
        last_update = data.get('last_update')
        if last_update:
            seven_days_ago = datetime.now() - timedelta(days=7)
            if last_update < seven_days_ago:
                self.should_stop = True
                self.logger.info(
                    f"Reached novel updated {last_update}, stopping crawl"
                )
        
        # ... continue with comment API call ...
```

---

## 4. GitHub Actions

### 4.1 daily-snapshot.yml (New)

```yaml
# .github/workflows/daily-snapshot.yml

name: Daily Snapshot

on:
  schedule:
    # UTC 20:00 = Shanghai 04:00
    - cron: "0 20 * * *"
  workflow_dispatch:

jobs:
  snapshot:
    runs-on: ubuntu-latest
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync

      - name: Create daily snapshot
        working-directory: website
        run: uv run python manage.py smart_snapshot
        env:
          DB_TYPE: postgresql
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          DEBUG: "0"
```

### 4.2 monthly-archive.yml (New)

```yaml
# .github/workflows/monthly-archive.yml

name: Monthly Archive

on:
  schedule:
    # UTC 21:00 = Shanghai 05:00, 1st of each month
    - cron: "0 21 1 * *"
  workflow_dispatch:

jobs:
  archive:
    runs-on: ubuntu-latest
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync

      - name: Archive last month snapshots
        working-directory: website
        run: uv run python manage.py archive_snapshots
        env:
          DB_TYPE: postgresql
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          DEBUG: "0"

      - name: Dump latest dataset
        working-directory: website
        run: uv run python manage.py dump_dataset release
        env:
          DB_TYPE: postgresql
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          DEBUG: "0"

      - name: Commit archived files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add release/dataset/
          git diff --cached --quiet || git commit -m "Archive snapshots for $(date -d 'last month' '+%Y-%m')"
          git push

      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: snapshot-${{ github.run_id }}
          name: "Snapshot $(date -d 'last month' '+%Y-%m')"
          body: |
            Monthly snapshot archive for $(date -d 'last month' '+%Y-%m')
            
            ## Contents
            - **snapshots**: Novel metrics for the past month
            - **dataset**: Full novel dataset
            
            ## Files
            - `snapshot_YYYY_MM.jsonl` - Snapshot data in JSONL format
            - `snapshot_YYYY_MM.csv` - Snapshot data in CSV format
            - `dataset/*.jsonl` - Full dataset in JSONL format
            - `dataset/*.csv` - Full dataset in CSV format
          files: |
            release/dataset/jsonl/snapshot_*.jsonl
            release/dataset/csv/snapshot_*.csv
            release/dataset/*.jsonl
            release/dataset/*.csv
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 5. File Summary

| File | Action | Description |
|------|--------|-------------|
| `website/novels/models.py` | Modify | Add NovelSnapshot, Task.LONG_TERM |
| `website/novels/admin.py` | Modify | Register NovelSnapshot |
| `website/novels/management/commands/smart_snapshot.py` | New | Daily snapshot |
| `website/novels/management/commands/archive_snapshots.py` | New | Monthly archive |
| `website/novels/management/commands/add_long_term.py` | New | Add long-term task |
| `website/novels/management/commands/remove_long_term.py` | New | Remove long-term task |
| `website/novels/management/commands/run_tasks.py` | Modify | Preserve long-term tasks |
| `meta_spider/meta_spider/pipelines.py` | Modify | Add SnapshotPipeline |
| `meta_spider/meta_spider/settings.py` | Modify | Enable pipeline |
| `meta_spider/meta_spider/spiders/meta_batch.py` | Modify | Add 7-day cutoff |
| `.github/workflows/daily-snapshot.yml` | New | Daily snapshot workflow |
| `.github/workflows/monthly-archive.yml` | New | Monthly archive workflow |

---

## 6. Implementation Order

```
1. Models + Migration
   ├── NovelSnapshot
   └── Task.LONG_TERM

2. Commands
   ├── smart_snapshot.py
   ├── archive_snapshots.py
   ├── add_long_term.py
   └── remove_long_term.py

3. Modify run_tasks.py

4. Scrapy
   ├── pipelines.py (SnapshotPipeline)
   ├── settings.py (enable pipeline)
   └── meta_batch.py (7-day cutoff)

5. GitHub Actions
   ├── daily-snapshot.yml
   └── monthly-archive.yml

6. Test
   └── uv run python manage.py test novels -v 2
```

---

## 7. Data Flow

```
Scrapy (manual/scheduled)
├── List page crawl
│   ├── Pages 1-N (ON_GOING, within 7 days)
│   ├── SnapshotPipeline → NovelSnapshot
│   └── Output JSONL (existing)
└── Long-term tasks
    ├── Manually added A-status
    └── SnapshotPipeline → NovelSnapshot

daily-snapshot (04:00 Shanghai)
├── smart_snapshot
│   ├── Fill gaps for ON_GOING not crawled by Scrapy
│   ├── Include long-term tasks
│   └── Delete snapshots older than 30 days

monthly-archive (05:00 Shanghai, 1st of month)
├── archive_snapshots
│   ├── Export snapshots to JSONL + CSV
│   └── Delete snapshots from DB
├── dump_dataset
│   └── Export full dataset to JSONL + CSV
├── Commit to GitHub
└── Create GitHub Release
    ├── snapshot_YYYY_MM.jsonl
    ├── snapshot_YYYY_MM.csv
    ├── dataset/*.jsonl
    └── dataset/*.csv
```

---

## 8. Commands Reference

```bash
# Daily operations
uv run python manage.py smart_snapshot          # Create daily snapshots

# Long-term tasks
uv run python manage.py add_long_term <nid>     # Add novel as long-term task
uv run python manage.py remove_long_term <nid>  # Remove long-term task
uv run python manage.py remove_long_term --all  # Remove all long-term tasks

# Archive
uv run python manage.py archive_snapshots                     # Archive last month (JSONL + CSV)
uv run python manage.py archive_snapshots --month 2026-01     # Archive specific month

# Existing commands
uv run python manage.py run_tasks               # Process tasks (preserves long-term)
uv run python manage.py fill_tasks              # Create tasks for duplicate covers
```
