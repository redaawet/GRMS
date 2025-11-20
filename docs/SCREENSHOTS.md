# Admin dashboard screenshot

The grouped admin dashboard can be captured locally for demos or documentation with the following steps:

1. Apply migrations and create a temporary superuser:
   ```bash
   python manage.py migrate
   DJANGO_SUPERUSER_PASSWORD=password123 python manage.py createsuperuser --noinput --username admin --email admin@example.com
   ```
2. Start the development server and capture the dashboard after logging in at http://127.0.0.1:8000/admin/ using the admin/password123 credentials.
3. Use the `browser_container` Playwright helper (or any headless browser) to take a full-page screenshot once the filter input with the `#dashboard-filter-input` id becomes visible.

The current review artifact lives at `browser:/invocations/sqbasvmp/artifacts/artifacts/grms-admin-dashboard.png`.
