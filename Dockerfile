FROM docker.m.daocloud.io/library/python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Node.js + pnpm (for Tailwind CSS build)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g pnpm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Create .env from example if not exists
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# Build Tailwind CSS
RUN cd website && pnpm install --frozen-lockfile && pnpm build

# Collect static files
RUN cd website && uv run python manage.py collectstatic --noinput 2>/dev/null || true

# Expose port
EXPOSE 8000

# Run with gunicorn (installed via uv)
CMD ["uv", "run", "--directory", "website", "python", "manage.py", "runserver", "0.0.0.0:8000"]
