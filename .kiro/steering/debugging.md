---
inclusion: manual
---

# Debugging & Troubleshooting

## Common Issues & Solutions

### Service Startup Issues
- **Port Conflicts**: Check if ports 5432, 5672, 8888, 8890 are available
- **Docker Issues**: Ensure Docker daemon is running
- **Health Checks**: Wait for PostgreSQL and RabbitMQ to be healthy
- **Environment**: Verify `.env` file exists in `infra/pvm/`

### Database Connection Problems
- **Connection String**: Check `POSTGRES_DSN` format
- **Service Order**: Ensure PostgreSQL starts before application services
- **Migrations**: Run migrations after PostgreSQL is ready
- **Permissions**: Verify database user permissions

### Message Queue Issues
- **RabbitMQ Health**: Check management UI at http://localhost:15672
- **Queue Bindings**: Verify topic bindings are correct
- **Dead Letters**: Check DLQ for failed messages
- **Connection Limits**: Monitor connection pool usage

### Vision Processing Errors
- **GPU Availability**: Check if NVIDIA runtime is available
- **Memory Issues**: Monitor GPU/CPU memory usage
- **Model Downloads**: Ensure CLIP models can be downloaded
- **Image Format**: Verify input image formats are supported

## Debugging Tools

### Logging
- **Structured Logs**: Use JSON format with appropriate levels
- **Service Logs**: `docker compose logs -f <service-name>`
- **Log Aggregation**: Consider centralized logging for production
- **Debug Level**: Set `LOG_LEVEL=DEBUG` for detailed output

### Monitoring
- **Health Endpoints**: Check `/health` on all services
- **Database UI**: Use PgWeb at http://localhost:8081
- **RabbitMQ Management**: Monitor queues and exchanges
- **System Stats**: Use `/stats` endpoint for metrics

### Development Tools
- **Hot Reload**: Code changes reflect immediately with volume mounts
- **Database Inspection**: Use PgWeb or direct SQL queries
- **Event Tracing**: Follow `job_id` through event logs
- **API Testing**: Use `/docs` endpoints for interactive testing

## Performance Debugging
- **Database Queries**: Use EXPLAIN ANALYZE for slow queries
- **Memory Usage**: Monitor container memory consumption
- **Processing Times**: Add timing logs to critical paths
- **Queue Depths**: Monitor RabbitMQ queue lengths

## Error Recovery
- **Service Restart**: Restart individual services without full rebuild
- **Data Cleanup**: Clear data directory if needed for fresh start
- **Queue Purging**: Purge RabbitMQ queues for clean state
- **Database Reset**: Drop and recreate database if corrupted