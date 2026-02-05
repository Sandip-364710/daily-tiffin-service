# Tiffin Service - Docker Setup

## Prerequisites
- Docker installed on your system
- Docker Compose installed

## Quick Start

### 1. Build and Run the Application
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

### 2. Access the Application
- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Database**: localhost:5432 (PostgreSQL)
- **Redis**: localhost:6379

### 3. Default Credentials
- **Admin**: admin / admin123
- **Database**: tiffin_user / tiffin_password

## Docker Services

### Web Service
- **Image**: Custom Django application
- **Port**: 8000
- **Dependencies**: PostgreSQL, Redis

### Database Service
- **Image**: PostgreSQL 15
- **Port**: 5432
- **Database**: tiffin_db
- **User**: tiffin_user
- **Password**: tiffin_password

### Redis Service
- **Image**: Redis 7 Alpine
- **Port**: 6379

## Development Commands

### Start Services
```bash
# Start all services
docker-compose up

# Start in detached mode
docker-compose up -d

# Rebuild and start
docker-compose up --build
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db
docker-compose logs redis
```

### Execute Commands
```bash
# Access Django shell
docker-compose exec web python manage.py shell

# Access database
docker-compose exec db psql -U tiffin_user -d tiffin_db

# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic
```

## Environment Variables

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_DB`: Database name (tiffin_db)
- `POSTGRES_USER`: Database user (tiffin_user)
- `POSTGRES_PASSWORD`: Database password (tiffin_password)

### Django Configuration
- `DEBUG`: Debug mode (1 for development)
- `SECRET_KEY`: Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

## Production Deployment

### Security Considerations
1. Change default passwords and secret keys
2. Set `DEBUG=0` in production
3. Use environment-specific configuration
4. Enable HTTPS
5. Configure proper logging

### Environment Variables for Production
```bash
DEBUG=0
SECRET_KEY=your-very-secure-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@db:5432/dbname
```

### Production Docker Compose
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database status
docker-compose exec db pg_isready -U tiffin_user

# Reset database
docker-compose down -v
docker-compose up --build
```

#### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :8000

# Change ports in docker-compose.yml
```

### Logs and Debugging
```bash
# View real-time logs
docker-compose logs -f web

# Check container status
docker-compose ps

# Inspect container
docker-compose inspect web
```

## Data Persistence

### Database Data
- Stored in Docker volume: `postgres_data`
- Persists across container restarts
- Back up regularly with `pg_dump`

### Static Files
- Collected in `staticfiles` directory
- Served by web server in production
- Can be mounted as volume for persistence

### Media Files
- User uploads and media content
- Should be backed up regularly
- Consider cloud storage for production

## Performance Optimization

### Database Optimization
- Use connection pooling
- Optimize queries
- Add indexes
- Regular maintenance

### Application Optimization
- Enable caching with Redis
- Use CDN for static files
- Optimize images
- Enable compression

### Docker Optimization
- Use multi-stage builds
- Optimize layer caching
- Use .dockerignore
- Monitor resource usage
