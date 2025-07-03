# Shoppersky Backend API

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

**A modern, high-performance event management API built with FastAPI**

[Features](#features) • [Quick Start](#quick-start) • [API Documentation](#api-documentation) • [Testing](#testing) • [Contributing](#contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Database](#database)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Shoppersky Backend is a robust, scalable REST API designed for comprehensive event management. Built with modern Python technologies, it provides a solid foundation for event-driven applications with features like role-based access control, category management, and media handling.

## ✨ Features

### 🔐 Authentication & Authorization
- **Role-Based Access Control (RBAC)** - Flexible permission system
- **JWT Authentication** - Secure token-based authentication
- **User Management** - Admin user creation and management

### 📊 Event Management
- **Category Management** - Hierarchical event categorization
- **Subcategory Support** - Nested category structures
- **Media Handling** - Image upload and management
- **SEO Optimization** - Meta titles, descriptions, and slugs

### 🛠 Developer Experience
- **Comprehensive Testing** - Unit, integration, and performance tests
- **API Documentation** - Auto-generated OpenAPI/Swagger docs
- **Type Safety** - Full Pydantic validation
- **Async/Await** - High-performance async operations

### 🚀 Production Ready
- **Docker Support** - Containerized deployment
- **Database Migrations** - SQLAlchemy with Alembic
- **Logging & Monitoring** - Structured logging
- **CORS Support** - Cross-origin resource sharing

## 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.115.13 |
| **Language** | Python 3.10+ |
| **Database** | PostgreSQL with AsyncPG |
| **ORM** | SQLAlchemy 2.0 (Async) |
| **Validation** | Pydantic v2 |
| **Testing** | Pytest with async support |
| **Containerization** | Docker & Docker Compose |
| **Documentation** | OpenAPI/Swagger |

## 📁 Project Structure

```
shoppersky-backend/
├── 📁 api/                          # API layer
│   └── 📁 v1/                       # API version 1
│       ├── 📁 endpoints/            # Route handlers
│       │   ├── categories.py        # Category CRUD operations
│       │   ├── categories_by_id.py  # Category operations by ID
│       │   ├── categories_by_slug.py # Category operations by slug
│       │   ├── subcategories.py     # Subcategory CRUD operations
│       │   ├── sub_categories_by_id.py
│       │   ├── sub_categories_by_slug.py
│       │   ├── roles.py             # Role management
│       │   ├── permissions.py       # Permission management
│       │   ├── role_permissions.py  # Role-permission mapping
│       │   └── media.py             # Media upload handling
│       └── routes.py                # Route registration
│
├── 📁 core/                         # Core application logic
│   ├── config.py                    # Application configuration
│   ├── auth.py                      # Authentication logic
│   ├── logging_config.py            # Logging configuration
│   ├── request_context.py           # Request context management
│   └── status_codes.py              # API response utilities
│
├── 📁 db/                           # Database layer
│   ├── 📁 models/                   # SQLAlchemy models
│   │   ├── base.py                  # Base model class
│   │   ├── user.py                  # User, Role, Permission models
│   │   └── categories.py            # Category and Subcategory models
│   └── 📁 sessions/                 # Database sessions
│       └── database.py              # Database connection setup
│
├── 📁 schemas/                      # Pydantic schemas
│   └── role_perm_schemas.py         # Role and permission schemas
│
├── 📁 services/                     # Business logic layer
│   └── category_service.py          # Category business logic
│
├── 📁 utils/                        # Utility functions
│   ├── file_uploads.py              # File upload utilities
│   ├── id_generators.py             # ID generation utilities
│   └── validators.py                # Custom validators
│
├── 📁 tests/                        # Test suite
│   ├── 📁 api/                      # API endpoint tests
│   │   └── 📁 roles/                # Role-specific tests
│   │       └── test_create_roles.py
│   ├── 📁 integration/              # Integration tests
│   │   └── test_database.py
│   ├── 📁 utils/                    # Test utilities
│   │   ├── api_helpers.py           # API testing helpers
│   │   ├── assertions.py            # Custom assertions
│   │   ├── db_helpers.py            # Database test helpers
│   │   ├── factories.py             # Test data factories
│   │   └── perf_tracker.py          # Performance tracking
│   ├── 📁 sandbox/                  # Experimental tests
│   └── conftest.py                  # Pytest configuration
│
├── 📁 scripts/                      # Utility scripts
│   └── manage_test_db.py            # Test database management
│
├── 📁 media/                        # Media storage
│   ├── 📁 categories/               # Category images
│   └── 📁 subcategories/            # Subcategory images
│
├── 📁 keys/                         # Security keys (not in repo)
├── main.py                          # Application entry point
├── lifespan.py                      # Application lifecycle management
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker configuration
├── docker-compose.yml               # Docker Compose setup
├── pytest.ini                      # Pytest configuration
├── run_tests.py                     # Advanced test runner
├── test.py                          # Simple test runner
├── TESTING.md                       # Testing documentation
└── README.md                        # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12+
- Docker (optional, for containerized deployment)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd shoppersky-backend
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# Application Settings
APP_NAME=Shoppersky API
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
FRONTEND_URL=http://localhost:3000

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=shoppersky

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Shoppersky API
```

### 5. Database Setup

```bash
# Create database (ensure PostgreSQL is running)
createdb shoppersky

# Run migrations (if using Alembic)
# alembic upgrade head
```

### 6. Run the Application

```bash
# Development server with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/events.json

## ⚙️ Configuration

The application uses environment-based configuration through `core/config.py`. Key settings include:

| Setting | Description | Default |
|---------|-------------|---------|
| `APP_NAME` | Application name | "FastAPI Application" |
| `ENVIRONMENT` | Runtime environment | "development" |
| `DATABASE_URL` | PostgreSQL connection string | Auto-generated |
| `MEDIA_ROOT` | Media files directory | "media/" |
| `MAX_UPLOAD_SIZE` | Maximum file upload size | 10MB |
| `ALLOWED_MEDIA_TYPES` | Supported media types | JPEG, PNG, GIF |

## 📚 API Documentation

### Core Endpoints

#### System Endpoints
- `GET /` - Welcome message and API information
- `GET /health` - Health check endpoint

#### Authentication & Authorization
- `POST /api/v1/roles/` - Create new role
- `GET /api/v1/roles/` - List all roles
- `PUT /api/v1/roles/{role_id}` - Update role
- `DELETE /api/v1/roles/{role_id}` - Delete role (soft delete)

#### Category Management
- `POST /api/v1/categories/` - Create category
- `GET /api/v1/categories/` - List categories
- `GET /api/v1/categories/{category_id}` - Get category by ID
- `GET /api/v1/categories/slug/{slug}` - Get category by slug
- `PUT /api/v1/categories/{category_id}` - Update category
- `DELETE /api/v1/categories/{category_id}` - Delete category

#### Subcategory Management
- `POST /api/v1/subcategories/` - Create subcategory
- `GET /api/v1/subcategories/` - List subcategories
- `GET /api/v1/subcategories/{subcategory_id}` - Get subcategory by ID
- `PUT /api/v1/subcategories/{subcategory_id}` - Update subcategory
- `DELETE /api/v1/subcategories/{subcategory_id}` - Delete subcategory

### Response Format

All API responses follow a consistent format:

```json
{
  "status_code": 200,
  "message": "Success message",
  "data": {
    // Response data
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Handling

Error responses include detailed information:

```json
{
  "status_code": 400,
  "detail": {
    "message": "Validation error",
    "errors": [
      {
        "field": "role_name",
        "message": "Field is required"
      }
    ]
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🗄️ Database

### Models Overview

#### User Management
- **Role**: User roles with permissions
- **Permission**: Individual permissions
- **RolePermission**: Many-to-many relationship
- **AdminUser**: Administrative users

#### Content Management
- **Category**: Event categories
- **SubCategory**: Event subcategories

### Database Features
- **Async Operations**: Full async/await support
- **Soft Deletes**: Logical deletion with status flags
- **Timestamps**: Automatic creation and update timestamps
- **Relationships**: Proper foreign key relationships
- **Constraints**: Unique constraints and validations

## 🧪 Testing

The project includes a comprehensive test suite with multiple testing approaches:

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Database and API integration
- **Performance Tests**: Load and performance testing

### Running Tests

```bash
# Run all tests (excluding slow tests)
pytest -m "not slow"

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m db           # Database tests only

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run tests in parallel
pytest -n auto

# Using the advanced test runner
python run_tests.py --unit --coverage --parallel

# Using the simple test runner
python test.py unit
```

### Test Structure
```
tests/
├── api/                 # API endpoint tests
├── integration/         # Integration tests
├── utils/              # Test utilities and helpers
├── sandbox/            # Experimental tests
└── conftest.py         # Pytest configuration and fixtures
```

For detailed testing information, see [TESTING.md](TESTING.md).

## 🐳 Docker Deployment

### Development with Docker

```bash
# Build the image
docker build -t shoppersky-backend .

# Run the container
docker run -p 8000:8000 --env-file .env shoppersky-backend
```

### Production Deployment

```bash
# Using Docker Compose (when available)
docker-compose up -d

# Or build for production
docker build -t shoppersky-backend:prod .
docker run -d -p 8000:8000 --env-file .env.production shoppersky-backend:prod
```

### Docker Features
- **Multi-stage builds**: Optimized image size
- **Non-root user**: Enhanced security
- **Health checks**: Container health monitoring
- **Environment configuration**: Flexible deployment options

## 💻 Development

### Code Style and Standards
- **Type Hints**: Full type annotation coverage
- **Async/Await**: Consistent async patterns
- **Pydantic Models**: Strong data validation
- **Error Handling**: Comprehensive error management

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following project conventions
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Tests**
   ```bash
   python run_tests.py --unit --integration --coverage
   ```

4. **Submit Pull Request**
   - Ensure all tests pass
   - Include descriptive commit messages
   - Update relevant documentation

### Adding New Endpoints

1. Create endpoint in `api/v1/endpoints/`
2. Add route to `api/v1/routes.py`
3. Create Pydantic schemas in `schemas/`
4. Add business logic to `services/`
5. Write comprehensive tests
6. Update API documentation

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write docstrings for public methods
- Maintain test coverage above 80%

### Pull Request Process
1. Update documentation for any new features
2. Ensure all tests pass
3. Add appropriate test coverage
4. Update the README if needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🚀 Application Commands

### Running the Application

#### Development Mode
```bash
# Method 1: Using main.py (recommended for development)
python main.py

# Method 2: Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Method 3: With custom host and port
uvicorn main:app --host 127.0.0.1 --port 8080 --reload

# Method 4: With specific reload delay
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-delay 15
```

#### Production Mode
```bash
# Basic production run
uvicorn main:app --host 0.0.0.0 --port 8000

# Production with workers (for better performance)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Production with SSL
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile ./keys/key.pem --ssl-certfile ./keys/cert.pem

# Using gunicorn for production (if installed)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Environment-Specific Commands
```bash
# Development environment
ENVIRONMENT=development python main.py

# Staging environment
ENVIRONMENT=staging uvicorn main:app --host 0.0.0.0 --port 8000

# Production environment
ENVIRONMENT=production uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Application URLs
Once running, access your application at:
- **Main API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/events.json
- **Media Files**: http://localhost:8000/media/

---

## 🧪 Comprehensive Testing Commands

### Basic Pytest Commands

#### Running All Tests
```bash
# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run all tests except slow ones (recommended for development)
pytest -m "not slow"

# Run all tests including slow ones
pytest -m "slow or not slow"
```

#### Running Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Database tests only
pytest -m db

# Authentication tests only
pytest -m auth

# Combine markers (unit tests that are not slow)
pytest -m "unit and not slow"
```

#### Running Specific Tests
```bash
# Run specific test file
pytest tests/api/roles/test_create_roles.py

# Run specific test function
pytest tests/api/roles/test_create_roles.py::test_create_role_success

# Run tests matching pattern
pytest -k "test_create"

# Run tests matching multiple patterns
pytest -k "test_create or test_update"

# Run tests in specific directory
pytest tests/api/

# Run tests with specific substring in name
pytest -k "role"
```

### Advanced Pytest Commands

#### Coverage Testing
```bash
# Basic coverage
pytest --cov=.

# Coverage with HTML report
pytest --cov=. --cov-report=html

# Coverage with terminal report
pytest --cov=. --cov-report=term-missing

# Coverage excluding test files
pytest --cov=. --cov-report=html --cov-exclude=tests/*

# Coverage with specific threshold
pytest --cov=. --cov-fail-under=80

# Combined coverage command
pytest --cov=. --cov-report=html --cov-report=term-missing --cov-exclude=tests/* --cov-fail-under=80
```

#### Parallel Testing
```bash
# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run tests with specific number of workers
pytest -n 4

# Parallel testing with coverage
pytest -n auto --cov=. --cov-report=html
```

#### Output and Debugging
```bash
# Show local variables in tracebacks
pytest -l

# Show full diff for assertions
pytest --tb=long

# Show short traceback
pytest --tb=short

# Show no traceback
pytest --tb=no

# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Show print statements
pytest -s

# Verbose output with print statements
pytest -v -s
```

#### Performance and Profiling
```bash
# Show slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0

# Profile tests (if pytest-profiling installed)
pytest --profile

# Memory profiling (if pytest-memray installed)
pytest --memray
```

### Using Custom Test Runners

#### Advanced Test Runner (run_tests.py)
```bash
# Basic usage
python run_tests.py

# Run specific test types
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --db
python run_tests.py --slow

# Run specific test file
python run_tests.py --file api/roles/test_create_roles.py

# Run specific test function
python run_tests.py --test test_create_role_success

# Run with coverage
python run_tests.py --coverage

# Run in parallel
python run_tests.py --parallel

# Combine options
python run_tests.py --unit --parallel --coverage
python run_tests.py --integration --coverage --verbose
```

#### Simple Test Runner (test.py)
```bash
# Run all tests (excluding slow)
python test.py

# Run specific categories
python test.py unit
python test.py integration
python test.py db
python test.py all

# Run specific file
python test.py tests/api/roles/test_create_roles.py

# Pass pytest arguments
python test.py -v
python test.py -k "test_create"
python test.py --help
```

### Database Testing Commands
```bash
# Run database-specific tests
pytest -m db

# Run tests with database cleanup
pytest -m db --setup-show

# Run database tests with specific database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test_db pytest -m db

# Manage test database
python scripts/manage_test_db.py create
python scripts/manage_test_db.py drop
python scripts/manage_test_db.py reset
```

### Continuous Integration Commands
```bash
# CI-friendly test run
pytest -v --tb=short --strict-markers --strict-config

# Full CI test suite
pytest -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing --cov-exclude=tests/* -m "not slow"

# Performance testing for CI
pytest -m "not slow" --durations=10
```

---

## 🛠 Development & Maintenance Commands

### Environment Management
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # if exists

# Update requirements
pip freeze > requirements.txt
```

### Database Management
```bash
# Create database
createdb shoppersky

# Drop database
dropdb shoppersky

# Connect to database
psql -d shoppersky

# Run database migrations (if using Alembic)
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "Description"

# Database backup
pg_dump shoppersky > backup.sql

# Database restore
psql shoppersky < backup.sql
```

### Code Quality Commands
```bash
# Format code with black (if installed)
black .
black --check .

# Sort imports with isort (if installed)
isort .
isort --check-only .

# Lint with flake8 (if installed)
flake8 .

# Type checking with mypy (if installed)
mypy .

# Security check with bandit (if installed)
bandit -r .
```

### Docker Commands
```bash
# Build Docker image
docker build -t shoppersky-backend .

# Build with specific tag
docker build -t shoppersky-backend:v1.0.0 .

# Run Docker container
docker run -p 8000:8000 shoppersky-backend

# Run with environment file
docker run -p 8000:8000 --env-file .env shoppersky-backend

# Run in detached mode
docker run -d -p 8000:8000 --name shoppersky-api shoppersky-backend

# View container logs
docker logs shoppersky-api

# Stop container
docker stop shoppersky-api

# Remove container
docker rm shoppersky-api

# Docker Compose commands
docker-compose up
docker-compose up -d
docker-compose down
docker-compose logs
docker-compose ps
```

### Utility Commands
```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check for outdated packages
pip list --outdated

# Generate requirements with versions
pip freeze > requirements.txt

# Install specific package version
pip install fastapi==0.115.13

# Uninstall package
pip uninstall package-name

# Clear Python cache
find . -type d -name __pycache__ -delete
find . -name "*.pyc" -delete

# Check disk usage of project
du -sh .

# Count lines of code
find . -name "*.py" -not -path "./venv/*" -not -path "./.pytest_cache/*" | xargs wc -l
```

### Monitoring & Debugging Commands
```bash
# Monitor application logs
tail -f logs/app.log  # if logging to file

# Check application health
curl http://localhost:8000/health

# Test API endpoints
curl -X GET http://localhost:8000/
curl -X GET http://localhost:8000/api/v1/roles/

# Monitor system resources
top
htop  # if installed
ps aux | grep python

# Check port usage
netstat -tulpn | grep :8000
lsof -i :8000  # on macOS/Linux
```

---

## 📞 Support

For support and questions:

- **Documentation**: Check the `/docs` endpoint when running
- **Issues**: Create an issue in the repository
- **Email**: Contact the development team

---

<div align="center">

**Built with ❤️ using FastAPI and modern Python**

[⬆ Back to Top](#shoppersky-backend-api)

</div>
