import asyncio

import pytest

from jsonapi.tests.app import app
from jsonapi.tests.db import *
from jsonapi.tests.data import TOTAL_USERS


@pytest.yield_fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def cli():
    return app.test_client()


@pytest.fixture()
async def article_count():
    return await pg.fetchval(articles_t.count())


@pytest.fixture()
def user_count():
    return TOTAL_USERS


@pytest.fixture()
def superuser_id():
    return 1


@pytest.fixture()
def user_1_id():
    return 25


@pytest.fixture()
def user_2_id():
    return 112
