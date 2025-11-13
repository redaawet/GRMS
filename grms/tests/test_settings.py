"""Tests that validate important runtime settings."""

from django.conf import settings
from django.test import SimpleTestCase


class SessionSettingsTests(SimpleTestCase):
    """Ensure the session backend stays cookie-based by default."""

    def test_default_session_engine_is_cookie_based(self):
        self.assertEqual(
            settings.SESSION_ENGINE,
            'django.contrib.sessions.backends.signed_cookies',
        )
