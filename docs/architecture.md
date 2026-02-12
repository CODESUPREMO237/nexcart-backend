# Architecture

This project follows clean architecture principles.

## Layers
- Domain: business entities and rules.
- Application: use-cases and services.
- Infrastructure: framework adapters and persistence.
- Interface: API handlers and serializers.

## Suggested Structure
- app/domain
- app/application
- app/infrastructure
- app/interfaces
- tests/unit
- tests/integration

## Quality Gates
- Linting via Flake8.
- Unit and integration tests via Pytest.
- Containerization with Docker.
