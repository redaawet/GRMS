GRMS Full System (Phase 1) - Backend scaffold

Quick start:
1. Clone this repository on your local machine and change into the project directory, for example:
   ```bash
   git clone <repository-url>
   cd GRMS
   ```
2. Create and activate a virtual environment, then install requirements: `pip install -r requirements.txt`
3. Configure a PostGIS database connection in `project/settings.py`
4. Apply database migrations: `python manage.py migrate`
5. Load the seed data (optional but recommended): `python manage.py loaddata fixtures.json`
6. Create an admin account: `python manage.py createsuperuser`
7. Start the development server: `python manage.py runserver`

## Codex Prompt for Calculated Fields

For implementing calculated database fields (MCI, prioritization score, ERA lookup quantities, BOQ aggregation, etc.), use the prompt saved at [`docs/codex_prompt.md`](docs/codex_prompt.md). It references the SRAD documents included in this repository and outlines the automated calculation requirements for Codex/Copilot.
