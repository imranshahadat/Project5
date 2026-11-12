alembic revision --autogenerate -m "init"
#  Generate the migration
alembic revision --autogenerate -m "initial async schema"

#  Apply it to your database
alembic upgrade head