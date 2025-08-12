# Running the Product-Video Matching System

This guide provides quick commands to run and manage the Product-Video Matching System using Docker Compose.

## 🚀 **Starting the System (Up)**

### Basic startup:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml up -d
```

### With rebuild (recommended after code changes):
```bash
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build
```

### View logs while starting:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml up --build
```

## 🛑 **Stopping the System (Down)**

### Stop services but keep data:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml down
```

### Stop services and remove volumes (⚠️ **deletes all data**):
```bash
docker compose -f infra/pvm/docker-compose.dev.yml down -v
```

### Stop and remove everything including images:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml down -v --rmi all
```

## 📊 **Monitoring Commands**

### Check service status:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml ps
```

### View logs:
```bash
# All services
docker compose -f infra/pvm/docker-compose.dev.yml logs -f

# Specific service
docker compose -f infra/pvm/docker-compose.dev.yml logs -f orchestrator
```

### Restart specific service:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml restart orchestrator
```

## 🎯 **Quick Commands (if you have the Makefile)**

If you're using the Makefile, you can use these shorter commands:

```bash
# Start system
make up-dev

# Stop system
make down

# View logs
make logs

# Restart specific service
make restart-orchestrator

# Check health
make health
```

## 🔧 **Complete Deployment Workflow**

Here's the recommended sequence for a fresh deployment:

```bash
# 1. Stop any existing containers
docker compose -f infra/pvm/docker-compose.dev.yml down -v

# 2. Start the system
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build

# 3. Wait for services to be ready (about 30 seconds)
sleep 30

# 4. Check status
docker compose -f infra/pvm/docker-compose.dev.yml ps

# 5. Seed the database (with correct connection string)
# On Windows PowerShell:
$env:POSTGRES_DSN="postgresql://postgres:dev@localhost:5435/postgres"
python scripts/seed.py

# On Linux/Mac:
POSTGRES_DSN="postgresql://postgres:dev@localhost:5435/postgres" python scripts/seed.py

# 6. Test the deployment
curl http://localhost:8080/health  # Results API
curl http://localhost:8000/health  # Orchestrator
```

## 🐛 **Troubleshooting Commands**

### If services are restarting:
```bash
# Check logs for errors
docker logs compose-orchestrator-1 --tail 20

# Rebuild specific service
docker compose -f infra/pvm/docker-compose.dev.yml build orchestrator
docker compose -f infra/pvm/docker-compose.dev.yml up -d orchestrator
```

### Clean slate restart:
```bash
# Nuclear option - removes everything
docker compose -f infra/pvm/docker-compose.dev.yml down -v --rmi all
docker system prune -f
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build
```

## 🌐 **Service Access Points**

Once the system is running, you can access:

- **PostgreSQL**: `localhost:5435` (user: postgres, password: dev)
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **RabbitMQ AMQP**: `localhost:5672`
- **Orchestrator API**: http://localhost:8000 (when running)
- **Results API**: http://localhost:8080 (when running)
- **Vector Index API**: http://localhost:8081 (when running)

## 📝 **Key Points**

- **Always use the full path**: `infra/pvm/docker-compose.dev.yml`
- **Use `-d` flag** for detached mode (runs in background)
- **Use `--build` flag** when you've made code changes
- **PostgreSQL runs on port 5435** (not the default 5432)
- **Wait for health checks** before testing APIs
- **Check logs** if services are restarting

## 🔍 **Health Checks**

Test if core services are working:

```bash
# Database connection test
docker exec compose-postgres-1 psql -U postgres -d postgres -c "SELECT 1;"

# RabbitMQ status
docker exec compose-rabbitmq-1 rabbitmqctl status

# Check all container status
docker compose -f infra/pvm/docker-compose.dev.yml ps
```

## 🚨 **Common Issues**

1. **Port conflicts**: If port 5435 is in use, change it in `docker-compose.dev.yml`
2. **Services restarting**: Check logs with `docker logs <container-name>`
3. **Import errors**: Application services may have Python import issues (infrastructure still works)
4. **Database connection**: Use port 5435, not 5432

The system should start up with PostgreSQL and RabbitMQ working perfectly. The application services may still have import issues, but the core infrastructure will be ready for development and testing!