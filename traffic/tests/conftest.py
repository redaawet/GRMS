import os

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from traffic.tests.fixtures import *  # noqa: F401,F403

@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(username="admin", password="pass", email="admin@example.com")


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    assert client.login(username=admin_user.username, password="pass")
    return client
