"""Serve the static build locally for preview."""

from functools import partial
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Serve build directory locally"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default="build",
            help="Static build directory (default: build)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8080,
            help="Port (default: 8080)",
        )
        parser.add_argument(
            "--base-path",
            default="",
            help="Base path prefix used during generate_static (e.g. novel_hub)",
        )

    def handle(self, *args, **options):
        directory = Path(options["dir"]).resolve()
        port = options["port"]
        base_path = options["base_path"].strip("/")

        if not directory.exists():
            self.stderr.write(f"Directory not found: {directory}")
            self.stderr.write("Run: uv run python manage.py generate_static")
            return

        if base_path:
            serve_dir = directory.parent
            url_prefix = f"/{base_path}/"
            self.stdout.write(
                f"Serving {serve_dir} at http://127.0.0.1:{port}{url_prefix}"
            )
        else:
            serve_dir = directory
            url_prefix = "/"
            self.stdout.write(
                f"Serving {serve_dir} at http://127.0.0.1:{port}{url_prefix}"
            )

        from http.server import HTTPServer, SimpleHTTPRequestHandler

        if base_path:

            class PrefixedHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(serve_dir), **kwargs)

                def translate_path(self, path):
                    if path.startswith(url_prefix):
                        path = path[len(url_prefix) - 1 :]
                    return super().translate_path(path)

            handler = PrefixedHandler
        else:
            handler = partial(SimpleHTTPRequestHandler, directory=str(directory))

        httpd = HTTPServer(("127.0.0.1", port), handler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")
