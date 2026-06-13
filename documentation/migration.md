1. docker-compose -f docker/docker-compose.yml exec api alembic revision --autogenerate -m "Initial migration"
2. docker-compose -f docker/docker-compose.yml exec api alembic upgrade head
w