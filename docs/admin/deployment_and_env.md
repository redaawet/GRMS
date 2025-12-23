# Deployment and environment guide

This guide explains how to configure environment variables, run the app locally with PostGIS, and prepare for production deployments.

## .env.example usage
1. Copy `.env.example` to `.env` in the project root.
2. Adjust credentials to match your PostGIS instance (user, password, host, port). The defaults align with the provided Docker Compose service.
3. Keep `USE_POSTGIS=true` and `ALLOW_SPATIAL_FALLBACK=false` so Django refuses to start without spatial libraries. Set `ALLOW_SPATIAL_FALLBACK=true` only for emergency debug sessions when PostGIS is unavailable.
4. Rotate `SECRET_KEY` before deploying and set `DEBUG=false` in any shared or production environment.
5. Optional superuser seeds (`SUPERUSER_*`) can be used by an initial data loader or admin script to create an admin account.

### Required environment variables
- `SECRET_KEY`: Django signing key (rotate per environment).
- `DEBUG`: `true`/`false`; must be `false` in production.
- `ALLOWED_HOSTS`: Comma-separated hostnames or IPs.
- `USE_POSTGIS`: Keep `true` for all test and production runs.
- `ALLOW_SPATIAL_FALLBACK`: Keep `false` so missing GDAL/GEOS fails fast.
- `POSTGRES_DB`, `POSTGRES_TEST_DB`: Default and test database names.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`: Connection details for the PostGIS instance.
- Optional GIS overrides: `GDAL_LIBRARY_PATH`, `GEOS_LIBRARY_PATH`, `GDAL_DATA`, and `PROJ_LIB` (only needed when the libraries are installed in non-standard locations).

## How to run locally (PostGIS-backed)
1. **Start PostGIS**: `docker compose up -d postgis` (uses `docker-compose.yml`).
2. **Install system deps**: ensure GDAL/GEOS libraries are available (on Ubuntu: `apt-get install gdal-bin libgdal-dev libgeos-dev postgresql-client`).
3. **Install Python deps**: `python -m pip install -r requirements.txt`.
4. **Apply migrations**: `python manage.py migrate` (uses the PostGIS database specified in `.env`).
5. **Run tests**: `pytest` (tests enforce PostGIS and will fail if GDAL/GEOS are missing).
6. **Compute indices**:
   - MCI: `python manage.py compute_mci 2024`
   - Prioritization: `python manage.py compute_benefits 2024` and `python manage.py compute_prioritization`
7. **Serve locally** (optional): `python manage.py runserver 0.0.0.0:8000` then log in via the custom grouped AdminSite.

## Production checklist
- `DEBUG=false`, hardened `SECRET_KEY`, and strict `ALLOWED_HOSTS`.
- PostGIS database provisioned with the `postgis` extension enabled.
- GDAL/GEOS installed on the host or base image (verify by importing `django.contrib.gis.gdal`).
- `.env` applied and secrets stored in your secret manager.
- Run `python manage.py migrate` before deploying code.
- Create an admin user and lock down superuser access; rotate passwords after hand-off.
- Configure HTTPS termination, CSRF trusted origins, and a proper media/static serving strategy.
- Schedule periodic runs for `compute_mci`, `compute_benefits`, and `compute_traffic_overall` if nightly refreshes are required.
