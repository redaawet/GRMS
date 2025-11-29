# Traffic test data and fixtures

This folder provides reusable, ERA-style traffic survey fixtures plus helper assets for testing and seeding.

## Running tests

- Run the full suite: `pytest`
- Target only this app: `pytest traffic`
- Run verbosely while skipping opt-out markers: `pytest -v -m "not skip"`
- Collect coverage for the traffic app: `pytest --cov=traffic`

## Loading sample data

The Django fixture includes a full 7-day traffic survey (cycle 1) with PCU and night adjustment lookups:

```bash
python manage.py loaddata traffic/fixtures/traffic_testdata.json
```

## Seeding via SQL

For manual database seeding (e.g., Postgres/PostGIS environments), use the SQL script:

```bash
psql -d dbname -f traffic/fixtures/traffic_seed.sql
```
