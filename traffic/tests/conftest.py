import os

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.utils import (
    setup_databases,
    setup_test_environment,
    teardown_databases,
    teardown_test_environment,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from traffic.tests.fixtures import *  # noqa: F401,F403


@pytest.fixture(scope="session", autouse=True)
def django_db_setup_session(request):
    try:
        setup_test_environment()
    except RuntimeError:
        # Already set up by pytest-django; continue without reinitializing.
        pass
    db_cfg = setup_databases(verbosity=0, interactive=False)

    def teardown():
        teardown_databases(db_cfg, verbosity=0)
        teardown_test_environment()

    request.addfinalizer(teardown)


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(username="admin", password="pass", email="admin@example.com")


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    assert client.login(username=admin_user.username, password="pass")
    return client
