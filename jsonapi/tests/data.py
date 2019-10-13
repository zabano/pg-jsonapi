import logging
import random
from math import ceil

import faker
from werkzeug.security import generate_password_hash

from jsonapi.tests import coroutine
from jsonapi.tests.db import *

logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RANDOM_SEED = 1980
TOTAL_USERS = 1000
MAX_ARTICLES_PER_USER = 6
SUPERUSER_MAX_ID = 10  # any user with an id under this value is a superuser
PUBLISHED_PROBABILITY = 0.90
COMMENT_PROBABILITY_PER_USER = 0.03  # probability of commenting on published articles
REPLY_PROBABILITY_PER_COMMENT = 0.75
MAX_COMMENT_REPLIES = 3
SQL_INSERT_LIMIT = 1000
DEFAULT_PASSWORD = generate_password_hash('welcome')


async def insert_data(conn, table, data):
    data = list(data.values()) if isinstance(data, dict) else data
    for i in range(0, len(data), SQL_INSERT_LIMIT):
        await conn.fetch(table.insert().values(data[i:i + SQL_INSERT_LIMIT]))


@coroutine
async def populate_test_db():
    await init_db()

    fake = faker.Faker('en_US')
    fake.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    async with pg.transaction() as conn:
        logger.info('start populating test database')

        #
        # truncate all tables
        #

        await conn.fetchrow('TRUNCATE TABLE test_data CASCADE')
        await conn.fetchrow('INSERT INTO test_data DEFAULT VALUES')

        logger.info('truncating user data ...')
        await conn.fetchrow('TRUNCATE TABLE users CASCADE')

        logger.info('truncating article data ...')
        await conn.fetchrow('TRUNCATE TABLE articles CASCADE')
        await conn.fetchrow('TRUNCATE TABLE keywords CASCADE')

        #
        # populate user data
        #

        logger.info('generating user data ...')
        user_data = {user_id: dict(
            id=user_id,
            email=fake.email(),
            created_on=fake.date_time_between(start_date="-1y", end_date="now", tzinfo=None),
            is_superuser=user_id < SUPERUSER_MAX_ID,
            password=DEFAULT_PASSWORD,
            status='pending' if user_id % 100 == 0 else 'active'
        ) for user_id in range(1, TOTAL_USERS + 1)}

        logger.info('creating {:,d} user accounts ...'.format(len(user_data)))
        await conn.fetch(users_t.insert().values(list(user_data.values())))

        logger.info('creating user name records ...')
        await conn.fetch(user_names_t.insert().values([dict(
            user_id=user_id,
            first=fake.first_name(),
            last=fake.last_name()
        ) for user_id in user_data.keys()]))

        logger.info('creating user bio records ...')
        await conn.fetch(user_bios_t.insert().values([dict(
            user_id=user_id,
            birthday=dt.datetime.strptime(fake.date(), '%Y-%m-%d')
            if user_id % 10 in (2, 6) else None,
            summary='\n'.join(fake.sentences(random.randint(3, 10)))
            if user_id % 10 in (6, 9) else None
        ) for user_id in user_data.keys() if random.randint(1, 10) == 5]))

        logger.info('creating followers ...')
        for user_id in user_data.keys():
            if user_id % 10 in random.sample(range(0, 10), 8):
                await conn.fetch(user_followers_t.insert().values([dict(
                    user_id=user_id,
                    follower_id=follower_id
                ) for follower_id in
                    random.sample(user_data.keys(), random.randint(1, int(TOTAL_USERS / 2)))
                    if follower_id != user_id]))

        #
        # populate article data
        #

        logger.info('generating articles ...')
        article_data = dict()
        article_id = 0
        for user_id in user_data.keys():
            user = user_data[user_id]
            for _ in range(1, random.randint(1, MAX_ARTICLES_PER_USER)):
                article_id += 1
                is_published = random.uniform(0, 1) <= PUBLISHED_PROBABILITY
                created_on = fake.date_time_between(start_date=user['created_on'], tzinfo=None)
                updated_on = fake.date_time_between(created_on, tzinfo=None) \
                    if random.randint(1, 10) == 5 else None
                article_data[article_id] = dict(
                    id=article_id,
                    title=fake.sentence(),
                    body='\n'.join(fake.sentences(random.randint(3, 10))),
                    created_on=created_on,
                    updated_on=updated_on,
                    author_id=user_id,
                    is_published=is_published,
                    published_by=random.randint(1, SUPERUSER_MAX_ID) if is_published else None)

        logger.info('creating {:,d} article records ...'.format(len(article_data)))
        await conn.fetch(articles_t.insert().values(list(article_data.values())))

        # keywords

        logger.info('generating article keywords ...')
        keyword_data = dict()
        keyword_id = 0
        keyword_articles = dict()
        for article in article_data.values():
            content = '{title} {body}'.format(title=article['title'].lower(),
                                              body=article['body'].replace('\n', ' '))
            for keyword in random.sample(content.split(' '), random.randint(0, 5)):
                keyword = keyword.strip('.').lower()
                if keyword not in keyword_data.keys():
                    keyword_id += 1
                    keyword_data[keyword] = dict(id=keyword_id, name=keyword)
                keyword_articles[(keyword_data[keyword]['id'], article['id'])] = dict(
                    article_id=article['id'],
                    keyword_id=keyword_data[keyword]['id'])

        logger.info('creating {:,d} keywords records ...'.format(len(keyword_data)))
        await conn.fetch(keywords_t.insert().values(list(keyword_data.values())))
        await conn.fetch(article_keywords_t.insert().values(list(keyword_articles.values())))

        # comments

        logger.info('generating comments ...')
        comment_data = dict()
        comment_id = 0
        for user_id in user_data.keys():
            for article_id in article_data.keys():
                article = article_data[article_id]
                comment_probability = random.uniform(0, 1)
                if comment_probability <= COMMENT_PROBABILITY_PER_USER and article['is_published']:
                    comment_id += 1
                    user_dt = user_data[user_id]['created_on']
                    article_dt = article['created_on']
                    created_on_start = user_dt if user_dt > article_dt else article_dt
                    created_on = fake.date_time_between(
                        start_date=created_on_start, end_date="now", tzinfo=None)
                    updated_on = fake.date_time_between(created_on, tzinfo=None) \
                        if random.randint(1, 50) == 5 else None
                    comment_data[comment_id] = dict(
                        id=comment_id,
                        article_id=article_id,
                        user_id=user_id,
                        body=' '.join(fake.sentences(random.randint(1, 3))),
                        created_on=created_on,
                        updated_on=updated_on)

        logger.info('creating {:,d} comment records ...'.format(len(comment_data)))
        await insert_data(conn, comments_t, comment_data)

        # replies

        logger.info('generating replies ...')
        reply_data = list()
        reply_id = 0
        for comment_id in comment_data.keys():
            for _ in range(0, MAX_COMMENT_REPLIES):
                reply_probability = random.uniform(0, 1)
                if reply_probability <= REPLY_PROBABILITY_PER_COMMENT:
                    reply_id += 1
                    created_on = fake.date_time_between(
                        start_date=comment_data[comment_id]['created_on'], end_date="now",
                        tzinfo=None)
                    updated_on = fake.date_time_between(created_on, tzinfo=None) \
                        if random.randint(1, 50) == 5 else None
                    reply_data.append(dict(
                        id=reply_id,
                        comment_id=comment_id,
                        user_id=random.choice(list(user_data.keys())),
                        body=' '.join(fake.sentences(random.randint(1, 2))),
                        created_on=created_on,
                        updated_on=updated_on
                    ))

        logger.info('creating {:,d} reply records ...'.format(len(reply_data)))
        await insert_data(conn, replies_t, reply_data)

        #
        # grant read access
        #

        logger.info('generating user access data ...')
        read_access_data = dict()

        # grant access to all users who commented on an article
        for comment in comment_data.values():
            article_id = comment['article_id']
            user_id = comment['user_id']
            author_id = article_data[article_id]['author_id']
            if user_id != author_id:
                read_access_data[(article_id, user_id)] = dict(
                    article_id=article_id, user_id=user_id)

        # grant access to all users who replied to comments on an article
        for reply in reply_data:
            article_id = comment_data[reply['comment_id']]['article_id']
            user_id = reply['user_id']
            author_id = article_data[article_id]['author_id']
            if user_id != author_id:
                read_access_data[(article_id, user_id)] = dict(
                    article_id=article_id, user_id=user_id)

        # grant access to all other random users
        for article in article_data.values():
            users = random.sample(user_data.keys(), random.randint(0, ceil(TOTAL_USERS / 20)))
            if article['author_id'] in users:
                users.remove(article['author_id'])
            read_access_data[(article_id, user_id)] = dict(
                article_id=article_id, user_id=user_id)

        logger.info('creating {:,d} read permission records ...'.format(len(read_access_data)))
        await insert_data(conn, article_read_access_t, read_access_data)

    #
    # done
    #

    logger.info('finished populating test database')
