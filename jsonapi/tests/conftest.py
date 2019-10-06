import asyncio

import pytest

from jsonapi.tests.data import TOTAL_USERS
from jsonapi.tests.db import *
from jsonapi.tests.model import ArticleModel, UserModel, TestModel


@pytest.yield_fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


#
# models
#

@pytest.fixture('session')
async def users():
    await init_db()
    return UserModel()


@pytest.fixture('session')
async def articles():
    await init_db()
    return ArticleModel()


#
# test data
#


@pytest.fixture('session')
async def test_data():
    await init_db()
    return await TestModel().get_object({}, 1)


@pytest.fixture('session')
async def article_count():
    return await pg.fetchval(articles_t.count())


@pytest.fixture('session')
def user_count():
    return TOTAL_USERS


@pytest.fixture('session')
async def superuser_id():
    return await pg.fetchval(sa.select([users_t.c.id]).select_from(
        users_t.join(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        users_t.c.is_superuser).group_by(users_t.c.id).limit(1))


@pytest.fixture('session')
async def user_1_id():
    return await pg.fetchval(sa.select([users_t.c.id]).select_from(
        users_t.join(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        ~users_t.c.is_superuser).group_by(users_t.c.id).limit(1))


@pytest.fixture('session')
async def user_1_article_id(user_1_id):
    return await pg.fetchval(sa.select([articles_t.c.id]).where(
        articles_t.c.author_id == user_1_id).limit(1))


@pytest.fixture('session')
async def user_1_article_id_forbidden(user_1_id):
    return await pg.fetchval(sa.select([articles_t.c.id]).where(
        articles_t.c.author_id.notin_(sa.select([article_read_access_t.c.article_id]).where(
            article_read_access_t == user_1_id))).limit(1))


@pytest.fixture('session')
async def user_1_article_id_readable(user_1_id):
    return await pg.fetchval(sa.select([article_read_access_t.c.article_id]).select_from(
        article_read_access_t.join(articles_t)).where(
        sa.and_(article_read_access_t.c.user_id == user_1_id,
                articles_t.c.author_id != user_1_id)).limit(1))


@pytest.fixture('session')
async def user_2_id():
    return await pg.fetchval(sa.select([users_t.c.id]).select_from(
        users_t.outerjoin(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        sa.and_(~users_t.c.is_superuser,
                articles_t.c.id.is_(None))).group_by(users_t.c.id).limit(1))
