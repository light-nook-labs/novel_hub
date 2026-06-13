"""Management command to serve static site for local preview.

Usage:
    uv run python manage.py serve_static --port 8080
"""

import http.server
import functools
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Serve static site for local preview"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="../build",
            help="Static files directory (default: ../build)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8080,
            help="Port to serve on (default: 8080)",
        )
        parser.add_argument(
            "--bind",
            type=str,
            default="0.0.0.0",
            help="Address to bind to (default: 0.0.0.0)",
        )

    def handle(self, *args, **options):
        directory = Path(options["dir"]).resolve()
        port = options["port"]
        bind = options["bind"]

        if not directory.exists():
            self.stderr.write(f"Directory does not exist: {directory}")
            return

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(directory),
        )

        self.stdout.write(f"Serving {directory} at http://{bind}:{port}")
        self.stdout.write("Press Ctrl+C to stop")

        with http.server.HTTPServer((bind, port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                self.stdout.write("\nStopped.")
