import datetime as dt
import enum

from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import false, text
from sqlalchemy.sql.schema import Column, ForeignKey, MetaData, PrimaryKeyConstraint, Table, \
    UniqueConstraint
from sqlalchemy.sql.sqltypes import BigInteger, Boolean, CHAR, Date, DateTime, Enum, Float, \
    Integer, JSON, Numeric, SmallInteger, String, Text, Time, VARCHAR

PASSWORD_HASH_LENGTH = 128

metadata = MetaData(schema='public')


@enum.unique
class UserStatus(enum.Enum):
    pending = 'Pending'
    active = 'Active'
    disabled = 'Disabled'


test_data_t = Table(
    'test_data', metadata,
    Column('test_bool', Boolean, nullable=False, index=True),
    Column('test_small_int', SmallInteger, nullable=False, index=True),
    Column('test_int', Integer, primary_key=True),
    Column('test_big_int', BigInteger, nullable=False, index=True),
    Column('test_float', Float, nullable=False, index=True),
    Column('test_double', Float, nullable=False, index=True),
    Column('test_numeric', Numeric(6, 4), nullable=False, index=True),
    Column('test_char', CHAR(10), nullable=False, index=True),
    Column('test_varchar', VARCHAR(100), nullable=False, index=True),
    Column('test_text', Text, nullable=False, index=True),
    Column('test_enum', Enum(UserStatus), nullable=False, index=True),
    Column('test_time', Time, nullable=False, index=True),
    Column('test_date', Date, nullable=False, index=True),
    Column('test_timestamp', DateTime, nullable=False, index=True),
    Column('test_timestamp_tz', DateTime(True), nullable=False, index=True),
    Column('test_json', JSON, nullable=False, index=True),
    Column('test_json_b', JSON, nullable=False, index=True))

users_t = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('email', Text, unique=True, nullable=False),
    Column('name', Text),
    Column('status', Enum(UserStatus), index=True, nullable=False,
           default=UserStatus.pending.name,
           server_default=text(UserStatus.pending.name)),
    Column('created_on', DateTime, nullable=False, default=dt.datetime.utcnow),
    Column('password', String(PASSWORD_HASH_LENGTH), nullable=False),
    Column('is_superuser', Boolean, default=False, server_default=false()))

user_bios_t = Table(
    'user_bios', metadata,
    Column('user_id', Integer,
           ForeignKey('users.id', ondelete='CASCADE', name='user_bios_id_fkey'),
           primary_key=True),
    Column('birthday', Date, index=True),
    Column('summary', Text))

user_names_t = Table(
    'user_names', metadata,
    Column('user_id', Integer,
           ForeignKey('users.id', ondelete='CASCADE', name='user_names_id_fkey'),
           primary_key=True, autoincrement=False),
    Column('title', Text),
    Column('first', Text, nullable=False),
    Column('middle', Text),
    Column('last', Text, nullable=False),
    Column('suffix', Text),
    Column('nickname', Text),
    UniqueConstraint('first', 'last'))

users_ts = Table(
    'users_ts', metadata,
    Column('user_id', Integer,
           ForeignKey('users.id', name='users_ts_article_id_fkey'),
           primary_key=True),
    Column('tsvector', TSVECTOR, index=True, nullable=False))

articles_t = Table(
    'articles', metadata,
    Column('id', Integer, primary_key=True),
    Column('author_id', Integer,
           ForeignKey('users.id', name='articles_author_id_fkey'),
           nullable=False, index=True),
    Column('published_by', Integer,
           ForeignKey('users.id', name='articles_published_by_fkey'),
           index=True),
    Column('title', Text, nullable=False, index=True),
    Column('body', Text, nullable=False),
    Column('created_on', DateTime(timezone=True)),
    Column('updated_on', DateTime(timezone=True)),
    Column('is_published', Boolean, nullable=False, default=False, server_default=false()))

articles_ts = Table(
    'articles_ts', metadata,
    Column('article_id', Integer,
           ForeignKey('articles.id', name='articles_ts_article_id_fkey'),
           primary_key=True),
    Column('tsvector', TSVECTOR, index=True, nullable=False))

comments_t = Table(
    'comments', metadata,
    Column('id', Integer, primary_key=True),
    Column('article_id', Integer,
           ForeignKey('articles.id', name='articles_article_id_fkey'),
           nullable=False, index=True),
    Column('user_id', Integer,
           ForeignKey('users.id', name='articles_user_id_fkey'),
           nullable=False, index=True),
    Column('body', Text, nullable=False),
    Column('created_on', DateTime(timezone=True)),
    Column('updated_on', DateTime(timezone=True)))

replies_t = Table(
    'replies', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer,
           ForeignKey('users.id', name='replies_user_id_fkey'),
           nullable=False, index=True),
    Column('comment_id', Integer,
           ForeignKey('comments.id', name='replies_comment_id_fkey'),
           nullable=False, index=True),
    Column('body', Text, nullable=False),
    Column('created_on', DateTime(timezone=True)),
    Column('updated_on', DateTime(timezone=True)))

keywords_t = Table(
    'keywords', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Text, nullable=False))

article_keywords_t = Table(
    'article_keywords', metadata,
    Column('article_id', Integer,
           ForeignKey('articles.id', ondelete='CASCADE',
                      name='article_keywords_article_id_fkey')),
    Column('keyword_id', Integer,
           ForeignKey('keywords.id', ondelete='CASCADE',
                      name='article_keywords_keyword_id_fkey')),
    PrimaryKeyConstraint('article_id', 'keyword_id'))

article_read_access_t = Table(
    'article_read_access', metadata,
    Column('article_id', Integer,
           ForeignKey('articles.id', ondelete='CASCADE',
                      name='article_read_access_article_id_fkey')),
    Column('user_id', Integer,
           ForeignKey('users.id', ondelete='CASCADE',
                      name='article_read_access_user_id_fkey')),
    PrimaryKeyConstraint('article_id', 'user_id'))
