# Running Tests

This project supports multiple ways to run your test suite. You can use `pytest` directly, or the provided helper scripts for more options and convenience.

## 1. Using `pytest` Directly

```sh
# Run all tests (except those marked as slow)
pytest -m "not slow" tests/

# Run all unit tests
pytest -m unit

# Run all integration tests
pytest -m integration

# Run all database tests
pytest -m db

# Run all tests including slow ones
pytest tests/

# Run a specific test file
pytest tests/api/test_roles.py

# Run a specific test function (by substring match)
pytest -k "test_create_role"

# Run tests with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing --cov-exclude=tests/*

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## 2. Using `run_tests.py` (Recommended for advanced options)

```sh
# Run all tests (except slow)
python run_tests.py

# Run all unit tests
python run_tests.py --unit

# Run all integration tests
python run_tests.py --integration

# Run all database tests
python run_tests.py --db

# Run all tests including slow ones
python run_tests.py --slow

# Run a specific test file
python run_tests.py --file api/test_roles.py

# Run a specific test function
python run_tests.py --test test_create_role

# Run with coverage report
python run_tests.py --coverage

# Run tests in parallel
python run_tests.py --parallel

# Combine options (e.g., parallel + coverage + only unit tests)
python run_tests.py --unit --parallel --coverage
```

## 3. Using `test.py` (Simple/Quick Runner)

```sh
# Run all tests (except slow)
python test.py

# Run all unit tests
python test.py unit

# Run all integration tests
python test.py integration

# Run all database tests
python test.py db

# Run all tests including slow ones
python test.py all

# Run a specific test file
python test.py tests/api/test_roles.py

# Run with any pytest options
python test.py -k "test_create_role"

# Show help
python test.py --help
```

---

**Note:**
- All commands assume you are in the project root directory.
- For parallel and coverage options, make sure you have the required plugins installed (`pytest-xdist`, `pytest-cov`).
- The scripts will print helpful errors if `pytest` is not installed.
