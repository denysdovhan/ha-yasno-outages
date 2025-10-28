# Technology Stack

## Programming Languages
- **Python 3.13.2+**: Primary language following Home Assistant core requirements
- **YAML**: Configuration files and examples

## Core Dependencies
- **Home Assistant 2025.10.4+**: Integration framework and runtime environment
- No external runtime dependencies (pure Home Assistant integration)

## Development Dependencies
- **pytest 8.3.5+**: Testing framework
- **pytest-asyncio 0.26.0+**: Async test support
- **pytest-cov 7.0.0+**: Code coverage reporting
- **ruff 0.14.2+**: Fast Python linter and formatter
- **pre-commit-uv 4.1.5+**: Git hooks for code quality

## Build System
- **uv**: Modern Python package manager (uv.lock present)
- **pyproject.toml**: PEP 621 compliant project configuration

## Development Tools

### Code Quality
- **Ruff**: Linting and formatting (.ruff.toml configuration)
- **Pre-commit**: Automated code quality checks (.pre-commit-config.yaml)
- **Coverage**: Code coverage tracking with HTML reports

### Testing
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=custom_components/svitlo_yeah --cov-report=html

# Platform-specific coverage scripts
script/coverage.sh   # Unix/Linux/macOS
script/coverage.bat  # Windows
```

### CI/CD
GitHub Actions workflows:
- **checks.yml**: Automated testing and linting
- **validate.yml**: Integration validation
- **release_draft.yml**: Automated release management

## Distribution
- **HACS (Home Assistant Community Store)**: Primary distribution method
- **GitHub Releases**: Version management and changelog
- **hacs.json**: HACS metadata configuration

## Configuration Files
- **manifest.json**: Home Assistant integration metadata (domain, version, IoT class)
- **pyproject.toml**: Python project configuration, dependencies, test settings
- **hacs.json**: HACS-specific metadata (name, country)
- **.ruff.toml**: Ruff linter/formatter configuration
- **.pre-commit-config.yaml**: Pre-commit hooks configuration

## Development Commands
```bash
# Install dependencies
uv sync

# Run linter
ruff check .

# Format code
ruff format .

# Run tests
pytest

# Run tests with coverage
pytest --cov

# Install pre-commit hooks
pre-commit install

# Run pre-commit checks
pre-commit run --all-files
```

## Version Management
- Version synchronized across pyproject.toml and manifest.json
- Semantic versioning (current: 0.5.1)
- Release drafts automated via GitHub Actions
