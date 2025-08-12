# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Product-Video Matching System.

## Quick Diagnostics

### System Health Check

```bash
# Check all services
make health

# Or manually check each service
curl http://localhost:8000/health  # Orchestrator
curl http://localhost:8080/health  # Results API
curl http://localhost:8081/health  # Vector Index
```

### Service Status

```bash
# Check Docker containers
docker compose -f infra/pvm/docker-compose.dev.yml ps

# Check logs
make logs

# Check specific service logs
make logs-orchestrator
```

### Database Connectivity

```bash
# Test database connection
docker exec postgres psql -U postgres -d postgres -c "SELECT 1;"

# Check database tables
docker exec postgres psql -U postgres -d postgres -c "\dt"
```

### Message Broker Status

```bash
# Check RabbitMQ status
docker exec rabbitmq rabbitmqctl status

# Check queues
docker exec rabbitmq rabbitmqctl list_queues

# Access management UI
open http://localhost:15672  # guest/guest
```

## Common Issues

### 1. Services Won't Start

#### Symptoms
- Docker containers exit immediately
- Port binding errors
- Health checks fail

#### Diagnosis
```bash
# Check container logs
docker compose logs orchestrator

# Check port conflicts
netstat -tulpn | grep :8000

# Check Docker daemon
docker info
```

#### Solutions

**Port Conflicts:**
```bash
# Find process using port
lsof -i :8000

# Kill process or change port in docker-compose.yml
```

**Permission Issues:**
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER ./data
```

**Resource Constraints:**
```bash
# Check available resources
docker system df
docker system prune  # Clean up unused resources

# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Memory > 8GB+
```

### 2. Database Connection Issues

#### Symptoms
- "Connection refused" errors
- Services can't connect to PostgreSQL
- Database queries timeout

#### Diagnosis
```bash
# Check PostgreSQL container
docker logs postgres

# Test connection from host
docker exec postgres pg_isready -U postgres

# Check connection from service container
docker exec orchestrator ping postgres
```

#### Solutions

**Container Not Ready:**
```bash
# Wait for PostgreSQL to be ready
docker compose up -d postgres
sleep 10
docker exec postgres pg_isready -U postgres
```

**Network Issues:**
```bash
# Check Docker network
docker network ls
docker network inspect product-video-matching_default

# Recreate network
docker compose down
docker compose up -d
```

**Configuration Issues:**
```bash
# Check environment variables
docker exec orchestrator env | grep POSTGRES

# Verify connection string format
# postgresql://user:password@host:port/database
```

### 3. RabbitMQ Connection Issues

#### Symptoms
- Message publishing fails
- Services can't subscribe to topics
- Queue backlog

#### Diagnosis
```bash
# Check RabbitMQ logs
docker logs rabbitmq

# Check connection from service
docker exec orchestrator ping rabbitmq

# Check queue status
docker exec rabbitmq rabbitmqctl list_queues
```

#### Solutions

**Authentication Issues:**
```bash
# Check RabbitMQ users
docker exec rabbitmq rabbitmqctl list_users

# Reset guest user
docker exec rabbitmq rabbitmqctl change_password guest guest
```

**Queue Backlog:**
```bash
# Purge queues (development only)
docker exec rabbitmq rabbitmqctl purge_queue products.collect.request

# Scale processing services
docker compose up -d --scale vision-embedding=3
```

**Memory Issues:**
```bash
# Check RabbitMQ memory usage
docker exec rabbitmq rabbitmqctl status

# Increase memory limit in docker-compose.yml
```

### 4. Job Processing Issues

#### Symptoms
- Jobs stuck in "collection" phase
- No products or videos created
- Matches not generated

#### Diagnosis
```bash
# Check job status
curl http://localhost:8000/status/{job_id}

# Check database for job data
docker exec postgres psql -U postgres -d postgres -c "
  SELECT j.job_id, j.phase, j.status,
         COUNT(DISTINCT p.product_id) as products,
         COUNT(DISTINCT v.video_id) as videos,
         COUNT(DISTINCT m.match_id) as matches
  FROM jobs j
  LEFT JOIN products p ON j.job_id = p.job_id
  LEFT JOIN videos v ON j.job_id = v.job_id
  LEFT JOIN matches m ON j.job_id = m.job_id
  WHERE j.job_id = '{job_id}'
  GROUP BY j.job_id, j.phase, j.status;
"

# Check service logs for errors
make logs-catalog-collector
make logs-media-ingestion
```

#### Solutions

**Stuck in Collection Phase:**
```bash
# Check if collection services are running
docker compose ps catalog-collector media-ingestion

# Restart collection services
docker compose restart catalog-collector media-ingestion

# Check for errors in logs
docker logs catalog-collector --tail 50
```

**No Products/Videos Created:**
```bash
# Check external API connectivity (mock in MVP)
# Verify data directory permissions
ls -la ./data/products/
ls -la ./data/videos/

# Check disk space
df -h
```

**Feature Extraction Issues:**
```bash
# Check vision services
docker compose ps vision-embedding vision-keypoint

# Check GPU availability (if using GPU)
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Check for CUDA/PyTorch issues in logs
docker logs vision-embedding --tail 50
```

### 5. Matching Performance Issues

#### Symptoms
- Very slow matching
- High CPU/memory usage
- Timeouts

#### Diagnosis
```bash
# Check resource usage
docker stats

# Check matching parameters
docker exec orchestrator env | grep -E "(RETRIEVAL|SIM_|MATCH_)"

# Check vector index performance
curl http://localhost:8081/stats
```

#### Solutions

**Slow Vector Search:**
```bash
# Check pgvector indexes
docker exec postgres psql -U postgres -d postgres -c "
  SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexname::regclass))
  FROM pg_indexes 
  WHERE tablename = 'product_images' AND indexname LIKE '%emb_%';
"

# Rebuild indexes if needed
docker exec postgres psql -U postgres -d postgres -c "
  REINDEX INDEX idx_product_images_emb_rgb;
  REINDEX INDEX idx_product_images_emb_gray;
"
```

**High Memory Usage:**
```bash
# Reduce batch sizes in vision services
# Edit docker-compose.yml to add environment variables:
# BATCH_SIZE=16  # Reduce from default 32

# Increase memory limits
docker update --memory=4g vision-embedding
```

**Timeout Issues:**
```bash
# Increase timeout values
# In .env file:
HTTP_TIMEOUT=120
PROCESSING_TIMEOUT=300

# Restart services
docker compose restart
```

### 6. API Response Issues

#### Symptoms
- 500 Internal Server Error
- Slow API responses
- Missing data in responses

#### Diagnosis
```bash
# Check API service logs
docker logs results-api --tail 50

# Test API endpoints
curl -v http://localhost:8080/results
curl -v http://localhost:8080/stats

# Check database queries
docker exec postgres psql -U postgres -d postgres -c "
  SELECT query, calls, total_time, mean_time 
  FROM pg_stat_statements 
  ORDER BY total_time DESC 
  LIMIT 10;
"
```

#### Solutions

**Database Query Performance:**
```bash
# Add missing indexes
docker exec postgres psql -U postgres -d postgres -c "
  CREATE INDEX IF NOT EXISTS idx_matches_job_score ON matches(job_id, score);
  CREATE INDEX IF NOT EXISTS idx_products_job_created ON products(job_id, created_at);
"

# Analyze query plans
docker exec postgres psql -U postgres -d postgres -c "
  EXPLAIN ANALYZE SELECT * FROM matches WHERE score >= 0.8 ORDER BY score DESC LIMIT 100;
"
```

**Memory Issues:**
```bash
# Increase API service memory
docker update --memory=2g results-api

# Add pagination to large queries
# Check API implementation for LIMIT/OFFSET usage
```

### 7. Data Storage Issues

#### Symptoms
- Images not found
- Evidence images missing
- Disk space errors

#### Diagnosis
```bash
# Check disk space
df -h ./data

# Check data directory structure
find ./data -type f | head -20

# Check file permissions
ls -la ./data/products/
ls -la ./data/videos/
ls -la ./data/evidence/
```

#### Solutions

**Disk Space:**
```bash
# Clean old data (development)
rm -rf ./data/products/*
rm -rf ./data/videos/*
rm -rf ./data/evidence/*

# Or clean specific job data
find ./data -name "*job_id*" -delete
```

**Permission Issues:**
```bash
# Fix permissions
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data
```

**Missing Files:**
```bash
# Check if services are writing to correct paths
docker exec catalog-collector ls -la /app/data/products/

# Verify volume mounts in docker-compose.yml
docker inspect catalog-collector | grep -A 10 Mounts
```

### 8. GPU Issues (If Using GPU)

#### Symptoms
- CUDA out of memory
- GPU not detected
- Slow embedding generation

#### Diagnosis
```bash
# Check GPU availability
nvidia-smi

# Check CUDA in container
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Check PyTorch GPU detection
docker exec vision-embedding python -c "import torch; print(torch.cuda.is_available())"
```

#### Solutions

**CUDA Out of Memory:**
```bash
# Reduce batch size
# In docker-compose.yml:
environment:
  - BATCH_SIZE=8  # Reduce from default 32
  - TORCH_CUDA_MEMORY_FRACTION=0.8
```

**GPU Not Detected:**
```bash
# Install NVIDIA Docker runtime
sudo apt install nvidia-docker2
sudo systemctl restart docker

# Enable GPU in docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - capabilities: [gpu]
```

## Performance Optimization

### Database Optimization

```sql
-- Add these to PostgreSQL configuration
shared_buffers = '2GB'
effective_cache_size = '6GB'
work_mem = '256MB'
maintenance_work_mem = '512MB'

-- Analyze tables regularly
ANALYZE products;
ANALYZE product_images;
ANALYZE videos;
ANALYZE video_frames;
ANALYZE matches;
```

### Application Optimization

```bash
# Tune connection pools
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30

# Optimize RabbitMQ
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_HEARTBEAT=60

# Tune processing
WORKER_CONCURRENCY=4
BATCH_SIZE=32
```

## Monitoring and Alerting

### Key Metrics to Monitor

```bash
# Service health
curl http://localhost:8080/health | jq '.status'

# System resources
docker stats --no-stream

# Queue depths
docker exec rabbitmq rabbitmqctl list_queues name messages

# Database performance
docker exec postgres psql -U postgres -d postgres -c "
  SELECT datname, numbackends, xact_commit, xact_rollback 
  FROM pg_stat_database 
  WHERE datname = 'postgres';
"
```

### Log Analysis

```bash
# Search for errors
docker logs orchestrator 2>&1 | grep -i error

# Monitor processing rates
docker logs matcher 2>&1 | grep "Processed.*matches" | tail -10

# Check for memory issues
docker logs vision-embedding 2>&1 | grep -i "memory\|oom"
```

## Recovery Procedures

### Service Recovery

```bash
# Restart individual service
docker compose restart orchestrator

# Restart all services
docker compose restart

# Full system restart
docker compose down
docker compose up -d
```

### Data Recovery

```bash
# Restore from backup (if available)
docker exec postgres psql -U postgres -d postgres < backup.sql

# Clear corrupted data
docker exec postgres psql -U postgres -d postgres -c "
  DELETE FROM matches WHERE job_id = 'corrupted_job_id';
  DELETE FROM video_frames WHERE video_id IN (
    SELECT video_id FROM videos WHERE job_id = 'corrupted_job_id'
  );
  DELETE FROM product_images WHERE product_id IN (
    SELECT product_id FROM products WHERE job_id = 'corrupted_job_id'
  );
  DELETE FROM videos WHERE job_id = 'corrupted_job_id';
  DELETE FROM products WHERE job_id = 'corrupted_job_id';
  DELETE FROM jobs WHERE job_id = 'corrupted_job_id';
"
```

## Getting Help

### Debug Information to Collect

When reporting issues, include:

1. **System Information:**
   ```bash
   docker --version
   docker compose version
   uname -a
   ```

2. **Service Status:**
   ```bash
   docker compose ps
   make health
   ```

3. **Logs:**
   ```bash
   docker compose logs --tail 100 > system-logs.txt
   ```

4. **Configuration:**
   ```bash
   cat .env | grep -v PASSWORD
   ```

5. **Resource Usage:**
   ```bash
   docker stats --no-stream
   df -h
   ```

### Support Channels

- Check existing GitHub issues
- Review documentation
- Create detailed issue report with debug information

### Emergency Procedures

**Complete System Failure:**
```bash
# Stop everything
docker compose down -v

# Clean Docker system
docker system prune -a

# Restart from scratch
make up-dev
make migrate
make seed
```

**Data Corruption:**
```bash
# Stop services
docker compose stop

# Backup current state
cp -r ./data ./data.backup

# Restore from known good backup
# Or clear and reseed data
rm -rf ./data/*
make seed
```

This troubleshooting guide covers the most common issues you might encounter. For complex problems, enable debug logging and analyze the detailed logs to identify the root cause.