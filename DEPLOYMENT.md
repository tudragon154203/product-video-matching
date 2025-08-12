# Deployment Guide

This guide covers deploying the Product-Video Matching System in different environments.

## Development Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM
- 20GB+ disk space

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd product-video-matching

# Setup environment
cp .env.example .env

# Start all services
make up-dev

# Initialize database
make migrate

# Seed with test data
make seed

# Verify deployment
make smoke
```

### Service Ports

- Main API: 8000
- Results API: 8080
- Vector Index: 8081
- PostgreSQL: 5432
- RabbitMQ: 5672 (Management: 15672)

## Production Deployment

### Infrastructure Requirements

#### Minimum Requirements

- **CPU**: 8 cores
- **RAM**: 16GB
- **Storage**: 100GB SSD
- **Network**: 1Gbps

#### Recommended Requirements

- **CPU**: 16 cores (with GPU: NVIDIA T4 or better)
- **RAM**: 32GB
- **Storage**: 500GB SSD
- **Network**: 10Gbps

### Environment Setup

#### 1. System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin postgresql-client

# Enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
```

#### 2. GPU Support (Optional)

```bash
# Install NVIDIA Docker runtime
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-docker2
sudo systemctl restart docker
```

#### 3. Production Configuration

Create production environment file:

```bash
# .env.production
POSTGRES_DSN=postgresql://produser:securepass@postgres:5432/proddb
BUS_BROKER=amqp://produser:securepass@rabbitmq:5672/
DATA_ROOT=/data
EMBED_MODEL=clip-vit-b32
LOG_LEVEL=INFO

# Security
POSTGRES_PASSWORD=your-secure-password
RABBITMQ_DEFAULT_USER=produser
RABBITMQ_DEFAULT_PASS=your-secure-password

# Performance tuning
RETRIEVAL_TOPK=50
POSTGRES_MAX_CONNECTIONS=100
RABBITMQ_VM_MEMORY_HIGH_WATERMARK=0.8
```

### Docker Compose Production

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: proddb
      POSTGRES_USER: produser
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_DEFAULT_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_DEFAULT_PASS}
      RABBITMQ_VM_MEMORY_HIGH_WATERMARK: ${RABBITMQ_VM_MEMORY_HIGH_WATERMARK}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  # Add all services with production configurations
  # Include resource limits, health checks, restart policies
```

### Kubernetes Deployment

#### 1. Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: product-video-matching

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: product-video-matching
data:
  EMBED_MODEL: "clip-vit-b32"
  LOG_LEVEL: "INFO"
  RETRIEVAL_TOPK: "50"
```

#### 2. Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: product-video-matching
type: Opaque
data:
  postgres-password: <base64-encoded-password>
  rabbitmq-password: <base64-encoded-password>
```

#### 3. Persistent Volumes

```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: product-video-matching
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
```

#### 4. Services Deployment

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: product-video-matching
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: postgres-password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

### Monitoring and Observability

#### 1. Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'product-video-matching'
    static_configs:
      - targets: ['main-api:8000', 'results-api:8080', 'vector-index:8081']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### 2. Grafana Dashboards

Key metrics to monitor:

- **System Health**: Service uptime, response times
- **Processing**: Jobs per hour, success rate
- **Resources**: CPU, memory, disk usage
- **Queue Depth**: RabbitMQ message counts
- **Database**: Connection pool, query performance

#### 3. Alerting Rules

```yaml
# monitoring/alerts.yml
groups:
- name: product-video-matching
  rules:
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.instance }} is down"

  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate on {{ $labels.instance }}"
```

### Backup and Recovery

#### 1. Database Backup

```bash
#!/bin/bash
# scripts/backup-db.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"

# Create backup
docker exec postgres pg_dump -U produser proddb > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "postgres_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 2. Data Volume Backup

```bash
#!/bin/bash
# scripts/backup-data.sh

DATA_DIR="/data"
BACKUP_DIR="/backups/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create incremental backup
rsync -av --link-dest="$BACKUP_DIR/latest" "$DATA_DIR/" "$BACKUP_DIR/$TIMESTAMP/"

# Update latest symlink
rm -f "$BACKUP_DIR/latest"
ln -s "$TIMESTAMP" "$BACKUP_DIR/latest"

echo "Data backup completed: $BACKUP_DIR/$TIMESTAMP"
```

### Security Hardening

#### 1. Network Security

```yaml
# docker-compose.prod.yml - Network isolation
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

services:
  nginx:
    networks:
      - frontend
      - backend
  
  orchestrator:
    networks:
      - backend
```

#### 2. Container Security

```dockerfile
# Use non-root user
FROM python:3.10-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Read-only filesystem
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Security scanning
RUN pip install --no-cache-dir safety
RUN safety check
```

#### 3. Secrets Management

```bash
# Use Docker secrets or Kubernetes secrets
docker secret create postgres_password /path/to/password/file
docker secret create rabbitmq_password /path/to/password/file
```

### Performance Optimization

#### 1. Database Tuning

```sql
-- postgresql.conf optimizations
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 256MB
maintenance_work_mem = 1GB
max_connections = 100
```

#### 2. Application Tuning

```bash
# Environment variables for production
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30
RABBITMQ_PREFETCH_COUNT=10
WORKER_CONCURRENCY=4
```

#### 3. Resource Limits

```yaml
# Docker Compose resource limits
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Scaling Strategies

#### 1. Horizontal Scaling

```yaml
# Scale processing services
docker compose up -d --scale vision-embedding=3 --scale matcher=2
```

#### 2. Load Balancing

```nginx
# nginx.conf
upstream main-api {
    server main-api-1:8000;
    server main-api-2:8000;
    server main-api-3:8000;
}

upstream results-api {
    server results-api-1:8080;
    server results-api-2:8080;
}
```

#### 3. Database Scaling

- **Read Replicas**: For Results API queries
- **Connection Pooling**: PgBouncer for connection management
- **Partitioning**: Time-based partitioning for large tables

### Troubleshooting Production Issues

#### 1. Common Issues

**High Memory Usage**:
```bash
# Check container memory usage
docker stats

# Adjust memory limits
docker update --memory=4g container_name
```

**Database Connection Exhaustion**:
```bash
# Check active connections
docker exec postgres psql -U produser -d proddb -c "SELECT count(*) FROM pg_stat_activity;"

# Increase connection limit
# In postgresql.conf: max_connections = 200
```

**Queue Backlog**:
```bash
# Check RabbitMQ queues
docker exec rabbitmq rabbitmqctl list_queues

# Scale processing services
docker compose up -d --scale vision-embedding=5
```

#### 2. Log Analysis

```bash
# Centralized logging with ELK stack
docker run -d --name elasticsearch elasticsearch:7.17.0
docker run -d --name kibana --link elasticsearch kibana:7.17.0

# Configure log shipping
# Use Filebeat or Fluentd to ship logs
```

### Maintenance Procedures

#### 1. Rolling Updates

```bash
#!/bin/bash
# scripts/rolling-update.sh

SERVICES=("main-api" "results-api" "vector-index")

for service in "${SERVICES[@]}"; do
    echo "Updating $service..."
    docker compose pull $service
    docker compose up -d --no-deps $service
    
    # Wait for health check
    sleep 30
    
    # Verify service is healthy
    if ! curl -f http://localhost:8080/health; then
        echo "Health check failed for $service"
        exit 1
    fi
done

echo "Rolling update completed successfully"
```

#### 2. Database Migrations

```bash
#!/bin/bash
# scripts/migrate-prod.sh

# Backup before migration
./scripts/backup-db.sh

# Run migrations
docker exec postgres psql -U produser -d proddb -f /migrations/latest.sql

# Verify migration
docker exec postgres psql -U produser -d proddb -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"
```

### Disaster Recovery

#### 1. Recovery Procedures

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

# Stop all services
docker compose down

# Restore database
gunzip -c /backups/postgres_backup_latest.sql.gz | docker exec -i postgres psql -U produser -d proddb

# Restore data volumes
rsync -av /backups/data/latest/ /data/

# Start services
docker compose up -d

# Verify system health
./scripts/health-check.sh
```

#### 2. Backup Verification

```bash
#!/bin/bash
# scripts/verify-backup.sh

# Test database backup
docker run --rm postgres:16 pg_restore --list /backups/postgres_backup_latest.sql.gz

# Test data integrity
find /data -type f -name "*.jpg" | head -10 | xargs file
```

This deployment guide provides comprehensive instructions for deploying the system in production environments with proper security, monitoring, and maintenance procedures.