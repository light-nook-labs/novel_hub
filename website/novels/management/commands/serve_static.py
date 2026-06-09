"""Serve the static build locally for preview."""

import os
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Serve static_build directory locally"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default="static_build",
            help="Static build directory (default: static_build)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8080,
            help="Port (default: 8080)",
        )

    def handle(self, *args, **options):
        directory = Path(options["dir"]).resolve()
        port = options["port"]

        if not directory.exists():
            self.stderr.write(f"Directory not found: {directory}")
            self.stderr.write("Run: uv run python manage.py generate_static")
            return

        os.chdir(directory)
        self.stdout.write(f"Serving {directory} at http://127.0.0.1:{port}")

        from http.server import HTTPServer, SimpleHTTPRequestHandler

        handler = SimpleHTTPRequestHandler
        httpd = HTTPServer(("127.0.0.1", port), handler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")
