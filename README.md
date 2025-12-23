GRMS Full System (Phase 1) - Backend scaffold

Quick start:
1. Clone this repository on your local machine and change into the project directory, for example:
   ```bash
   git clone <repository-url>
   cd GRMS
   ```
2. Create and activate a virtual environment, then install requirements: `pip install -r requirements.txt`
   - On Debian/Ubuntu you may need system geospatial libraries for `pyproj` and PostGIS builds:
     ```bash
     sudo apt-get update
     sudo apt-get install -y libproj-dev proj-data proj-bin libgeos-dev
     ```
   - If you are compiling against PostGIS locally, also install `postgresql-server-dev-15` (or your PostgreSQL major version).
3. Configure a PostGIS database connection in `project/settings.py` or by copying `.env.example` to `.env` and updating the values.
4. Apply database migrations: `python manage.py migrate`
5. Load the seed data (optional but recommended): `python manage.py loaddata fixtures.json`
6. Create an admin account: `python manage.py createsuperuser`
7. Start the development server: `python manage.py runserver`

### Additional docs
- Admin operations and workflows: [`docs/user_manual/phase1_admin_manual.md`](docs/user_manual/phase1_admin_manual.md)
- Role capabilities: [`docs/user_manual/role_guides.md`](docs/user_manual/role_guides.md)
- Import templates: [`docs/user_manual/import_templates.md`](docs/user_manual/import_templates.md)
- Deployment and environment setup (includes \"How to run locally\"): [`docs/admin/deployment_and_env.md`](docs/admin/deployment_and_env.md)

## Codex Prompt for Calculated Fields

For implementing calculated database fields (MCI, prioritization score, ERA lookup quantities, BOQ aggregation, etc.), use the prompt saved at [`docs/codex_prompt.md`](docs/codex_prompt.md). It references the SRAD documents included in this repository and outlines the automated calculation requirements for Codex/Copilot.
