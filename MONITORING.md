# Docker Container Monitoring

This project includes a streamlined monitoring stack focused exclusively on **Docker container metrics** - no host/system monitoring, just pure container insights.

## Components

### 1. **Prometheus** (Port 9090)
- Time-series database for metrics collection
- Scrapes container metrics every 5 seconds
- 30-day data retention
- Persistent storage via Docker volume

### 2. **Grafana** (Port 3000)
- Visualization and dashboarding
- Pre-configured "Docker Container Monitoring" dashboard
- Default login: admin/admin (change on first login)

### 3. **Docker Stats Exporter** (Port 9487)
- Exports individual container metrics (CPU, memory, network, disk I/O)
- Works perfectly on macOS, Linux, and Windows
- Lightweight and reliable

## Quick Start

```bash
# Start the monitoring stack
docker-compose up -d

# Check health status
docker ps --filter "name=prometheus|grafana|docker-exporter"

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana Dashboard | http://localhost:3000/d/docker-containers | Container monitoring dashboard |
| Grafana Home | http://localhost:3000 | Dashboards and settings |
| Prometheus | http://localhost:9090 | Metrics and queries |
| Docker Exporter | http://localhost:9487/metrics | Raw container metrics |

## Container Metrics Available

The Docker Stats Exporter provides the following metrics for **each running container**:

### CPU Metrics
- `dockerstats_cpu_usage_ratio` - CPU usage percentage (0-100)

### Memory Metrics
- `dockerstats_memory_usage_bytes` - Current memory usage in bytes
- `dockerstats_memory_limit_bytes` - Memory limit for the container

### Network Metrics
- `dockerstats_network_rx_bytes` - Total bytes received
- `dockerstats_network_tx_bytes` - Total bytes transmitted

### Disk I/O Metrics
- `dockerstats_block_read_bytes` - Total bytes read from disk
- `dockerstats_block_write_bytes` - Total bytes written to disk

All metrics include labels:
- `name` - Container name
- `id` - Container ID
- `instance` - Exporter instance
- `job` - Prometheus job name

## Dashboard Features

The **Docker Container Monitoring** dashboard shows:

1. **Container CPU Usage (%)** - Bar gauge showing CPU usage for all containers
2. **Container Memory Usage** - Bar gauge showing memory consumption
3. **Container CPU Usage Over Time** - Time series graph tracking CPU trends
4. **Container Memory Usage Over Time** - Time series graph tracking memory trends
5. **Container Network Traffic** - RX/TX bytes per second
6. **Container Disk I/O** - Read/Write operations per second

Auto-refreshes every 5 seconds for real-time monitoring.

## Useful PromQL Queries

```promql
# Top 5 containers by CPU usage
topk(5, dockerstats_cpu_usage_ratio)

# Containers using more than 100MB RAM
dockerstats_memory_usage_bytes > 100000000

# Network traffic rate (bytes per second)
rate(dockerstats_network_rx_bytes[1m])
rate(dockerstats_network_tx_bytes[1m])

# Disk I/O rate (bytes per second)
rate(dockerstats_block_read_bytes[1m])
rate(dockerstats_block_write_bytes[1m])

# Total memory used by all containers
sum(dockerstats_memory_usage_bytes)

# Number of running containers
count(dockerstats_cpu_usage_ratio)
```

## Configuration

### Environment Variables

Add to your `.env` file (optional):

```bash
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090
DOCKER_EXPORTER_PORT=9487
```

### Prometheus Configuration

Edit `prometheus/prometheus.yml` to:
- Adjust scrape intervals
- Add alerting rules
- Configure remote storage

Reload configuration without restart:
```bash
curl -X POST http://localhost:9090/-/reload
```

## Health Checks

Check monitoring stack health:

```bash
# Check all monitoring containers
docker ps --filter "name=prometheus|grafana|docker-exporter"

# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check if metrics are flowing
curl -s http://localhost:9090/api/v1/query?query=dockerstats_cpu_usage_ratio | jq '.data.result | length'
```

## Troubleshooting

### No container metrics showing

1. **Check docker-exporter is running:**
   ```bash
   docker logs docker-exporter
   ```

2. **Verify metrics are exposed:**
   ```bash
   curl http://localhost:9487/metrics | grep dockerstats_cpu
   ```

3. **Check Prometheus is scraping:**
   - Go to http://localhost:9090/targets
   - Look for `docker-containers` job
   - Should show status "UP"

### Grafana dashboard is empty

1. **Wait a minute** - Prometheus needs time to scrape initial metrics
2. **Check datasource connection:**
   - Go to http://localhost:3000/datasources
   - Click "Prometheus"
   - Click "Test" button
3. **Verify data in Prometheus:**
   - Go to http://localhost:9090
   - Run query: `dockerstats_cpu_usage_ratio`
   - Should show data for all containers

### Docker exporter permission issues

If docker-exporter can't access Docker socket:

```yaml
# In docker-compose.yml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

Ensure Docker socket has proper permissions (usually works out of the box).

## Data Retention

- **Prometheus**: 30 days (configurable via `--storage.tsdb.retention.time`)
- **Grafana**: Persistent dashboards and settings

To increase retention:
```yaml
command:
  - '--storage.tsdb.retention.time=90d'  # 90 days
  - '--storage.tsdb.retention.size=50GB'  # Size limit
```

## Why This Setup?

✅ **Simple** - Only monitors containers, not the host OS
✅ **Cross-platform** - Works on macOS, Linux, Windows
✅ **Lightweight** - Minimal resource overhead
✅ **Production-ready** - Battle-tested components
✅ **Real-time** - 5-second refresh interval
✅ **Persistent** - Data survives container restarts

## What This Setup Does NOT Include

❌ Host CPU/Memory/Disk monitoring (node-exporter)
❌ Low-level container metrics (cAdvisor)
❌ Application-specific metrics (unless exposed)
❌ Log aggregation (Loki/ELK)
❌ Alerting (Alertmanager)

**This is intentional** - the focus is purely on Docker container metrics for simplicity and clarity.

## Extending the Setup

Want to add more monitoring? Consider:

1. **LiteLLM metrics** - Already configured in Prometheus
2. **Custom application metrics** - Expose `/metrics` endpoint
3. **Alerting** - Add Prometheus Alertmanager
4. **Log aggregation** - Add Loki + Promtail

The current setup is a solid foundation you can build upon!
