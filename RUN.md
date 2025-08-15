# Running the Product-Video Matching System

This guide provides quick commands to run and manage the Product-Video Matching System using Docker Compose.

## 🚀 **Starting the System (Up)**

### Basic startup:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml up -d
```

### With rebuild (recommended after requirement/base lib changes):
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
docker compose -f infra/pvm/docker-compose.dev.yml logs -f main-api
```

### Start/Stop Individual Services:

#### ▶️ Start a specific service:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml up -d --no-deps <service_name>
```

#### ⏹️ Stop a specific service:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml stop <service_name>
```

#### 🔄 Restart specific service:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml restart <service_name>
```

#### 🛠️ Rebuild specific service:
```bash
docker compose -f infra/pvm/docker-compose.dev.yml build <service_name>
docker compose -f infra/pvm/docker-compose.dev.yml up -d --no-deps <service_name>
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
make restart-main-api

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

# 5. Run database migrations
# On Windows PowerShell:
.\migrate.ps1

# On Linux/Mac:
./migrate.ps1

# 6. Test the deployment
curl http://localhost:8080/health  # Results API
curl http://localhost:8000/health  # Main API
```

## 🐛 **Troubleshooting Commands**

### If services are restarting:
```bash
# Check logs for errors
docker logs product-video-matching-main-api-1 --tail 20

# Rebuild specific service
docker compose -f infra/pvm/docker-compose.dev.yml build main-api
docker compose -f infra/pvm/docker-compose.dev.yml up -d main-api
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
- **Main API**: http://localhost:8000 (when running)
- **Results API**: http://localhost:8080 (when running)
- **PostgreSQL Web UI**: http://localhost:8081 (when running)

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
docker exec product-video-matching-postgres-1 psql -U postgres -d postgres -c "SELECT 1;"

# RabbitMQ status
docker exec product-video-matching-rabbitmq-1 rabbitmqctl status

# Check all container status
docker compose -f infra/pvm/docker-compose.dev.yml ps
```

## 🚨 **Common Issues**

1. **Port conflicts**: If port 5435 is in use, change it in `docker-compose.dev.yml`
2. **Services restarting**: Check logs with `docker logs <container-name>`
3. **Import errors**: Application services may have Python import issues (infrastructure still works)
4. **Database connection**: Use port 5435, not 5432

The system should start up with PostgreSQL and RabbitMQ working perfectly. The application services may still have import issues, but the core infrastructure will be ready for development and testing!