# Pydantic AI Production Ready Template

## First Time Setup

Follow these steps to get started with the project:

### 1. Install Dependencies

```bash
make install-dev
```

This will install all project dependencies including development tools.

### 2. Configure Environment Variables

Copy the example environment file and update it with your values:

```bash
cp .env.example .env.development
```

Edit `.env.development` and update the following:

- **LOGFIRE_TOKEN**: Get your token from [Logfire](https://logfire.pydantic.dev) (see instructions below)
- **DATABASE_***: Update database credentials if needed (defaults work with Docker)
- **PGADMIN_***: Configure pgAdmin credentials if needed

### 3. Configure LOGFIRE_TOKEN

1. Sign in to https://logfire.pydantic.dev
2. Go to projects
3. Go to New project
4. Add project name and select visibility to Private
5. After this you will be redirected to Settings page of the project you have created
6. Go to write tokens and press on "New write token" to create a new token
7. Copy the token and add it to your `.env.development` file as `LOGFIRE_TOKEN=your_token_here`

### 4. Start Docker Services

Start PostgreSQL, pgAdmin, and other services:

```bash
make docker-dev-up
```

This will start:
- PostgreSQL 17 (port 5432)
- pgAdmin 4 (port 5050, default: admin@admin.com / admin)
- Redis (port 6379)
- LiteLLM (port 4000)
- Ollama (port 11434)

**Container Monitoring:**
- Grafana (port 3000) - Dashboards and visualization
- Prometheus (port 9090) - Metrics collection
- Docker Exporter (port 9487) - Container metrics

> 📊 **View Container Metrics**: http://localhost:3000/d/docker-containers
> 📖 For detailed monitoring documentation, see [MONITORING.md](MONITORING.md)

#### Quick Access

- **Container Dashboard**: http://localhost:3000/d/docker-containers
- **Grafana Home**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **pgAdmin**: http://localhost:5050 (admin@admin.com/admin)

### 5. Run Database Migrations

Create and apply the initial database schema:

```bash
make migration-create MESSAGE="initial migration"
make migration-upgrade
```

### 6. Start the Application

Run the FastAPI application in development mode:

```bash
make run-dev
```

The application will be available at `http://localhost:8000`

### 7. (Optional) Install Pre-commit Hooks

To automatically run linting and formatting on commit:

```bash
make pre-commit-install
```

## Common Commands

- `make help` - Show all available commands
- `make run-dev` - Run the application in development mode
- `make docker-dev-up` - Start all Docker services
- `make docker-dev-down` - Stop all Docker services
- `make migration-upgrade` - Apply database migrations
- `make format` - Format code with Ruff
- `make test` - Run tests

