import asyncio

import pytest
from asyncpgsa import pg
from sqlalchemy.sql import and_, func, select

from jsonapi.tests.data import TOTAL_USERS
from jsonapi.tests.db import *
from jsonapi.tests.model import ArticleModel, KeywordModel, TestModel, UserModel


@pytest.yield_fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session', autouse=True)
def init_pg(event_loop):
    event_loop.run_until_complete(pg.init(
        database='jsonapi',
        user='jsonapi',
        password='jsonapi',
        min_size=5,
        max_size=10
    ))


#
# models
#

@pytest.fixture()
def users():
    return UserModel()


@pytest.fixture()
def articles():
    return ArticleModel()


@pytest.fixture()
def keywords():
    return KeywordModel()


#
# test data
#


@pytest.fixture(scope='session')
async def test_data():
    return await TestModel().get_object({}, 1)


@pytest.fixture(scope='session')
async def article_count():
    return await pg.fetchval(select([func.count()]).select_from(articles_t))


@pytest.fixture(scope='session')
def user_count():
    return TOTAL_USERS


@pytest.fixture(scope='session')
async def superuser_id():
    return await pg.fetchval(select([users_t.c.id]).select_from(
        users_t.join(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        users_t.c.is_superuser).group_by(users_t.c.id).limit(1))


@pytest.fixture(scope='session')
async def user_1_id():
    return await pg.fetchval(select([users_t.c.id]).select_from(
        users_t.join(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        ~users_t.c.is_superuser).group_by(users_t.c.id).limit(1))


@pytest.fixture(scope='session')
async def user_1_article_id(user_1_id):
    return await pg.fetchval(select([articles_t.c.id]).where(
        articles_t.c.author_id == user_1_id).limit(1))


@pytest.fixture(scope='session')
async def user_1_article_id_forbidden(user_1_id):
    return await pg.fetchval(select([articles_t.c.id]).where(
        articles_t.c.author_id.notin_(select([article_read_access_t.c.article_id]).where(
            article_read_access_t == user_1_id))).limit(1))


@pytest.fixture(scope='session')
async def user_1_article_id_readable(user_1_id):
    return await pg.fetchval(select([article_read_access_t.c.article_id]).select_from(
        article_read_access_t.join(articles_t)).where(
        and_(article_read_access_t.c.user_id == user_1_id,
             articles_t.c.author_id != user_1_id)).limit(1))


@pytest.fixture(scope='session')
async def user_2_id():
    return await pg.fetchval(select([users_t.c.id]).select_from(
        users_t.outerjoin(articles_t, articles_t.c.author_id == users_t.c.id)).where(
        and_(~users_t.c.is_superuser,
             articles_t.c.id.is_(None))).group_by(users_t.c.id).limit(1))
