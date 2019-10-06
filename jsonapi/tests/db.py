import datetime as dt
import enum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

PASSWORD_HASH_LENGTH = 128

metadata = sa.MetaData(schema='public')


@enum.unique
class UserStatus(enum.Enum):
    pending = 'Pending'
    active = 'Active'
    disabled = 'Disabled'


test_data_t = sa.Table(
    'test_data', metadata,
    sa.Column('test_bool', sa.Boolean, nullable=False, index=True),
    sa.Column('test_small_int', sa.SmallInteger, nullable=False, index=True),
    sa.Column('test_int', sa.Integer, primary_key=True),
    sa.Column('test_big_int', sa.BigInteger, nullable=False, index=True),
    sa.Column('test_float', sa.Float, nullable=False, index=True),
    sa.Column('test_double', sa.Float, nullable=False, index=True),
    sa.Column('test_numeric', sa.Numeric(6, 4), nullable=False, index=True),
    sa.Column('test_char', sa.CHAR(10), nullable=False, index=True),
    sa.Column('test_varchar', sa.VARCHAR(100), nullable=False, index=True),
    sa.Column('test_text', sa.Text, nullable=False, index=True),
    sa.Column('test_enum', sa.Enum(UserStatus), nullable=False, index=True),
    sa.Column('test_time', sa.Time, nullable=False, index=True),
    sa.Column('test_date', sa.Date, nullable=False, index=True),
    sa.Column('test_timestamp', sa.DateTime, nullable=False, index=True),
    sa.Column('test_timestamp_tz', sa.DateTime(True), nullable=False, index=True),
    sa.Column('test_json', sa.JSON, nullable=False, index=True),
    sa.Column('test_json_b', sa.JSON, nullable=False, index=True))

users_t = sa.Table(
    'users', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('email', sa.Text, unique=True, nullable=False),
    sa.Column('name', sa.Text),
    sa.Column('status', sa.Enum(UserStatus), index=True, nullable=False,
              default=UserStatus.pending.name,
              server_default=sa.text(UserStatus.pending.name)),
    sa.Column('created_on', sa.DateTime, nullable=False, default=dt.datetime.utcnow),
    sa.Column('password', sa.String(PASSWORD_HASH_LENGTH), nullable=False),
    sa.Column('is_superuser', sa.Boolean, default=False, server_default=sa.false()))

user_bios_t = sa.Table(
    'user_bios', metadata,
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', ondelete='CASCADE', name='user_bios_id_fkey'),
              primary_key=True),
    sa.Column('birthday', sa.Date, index=True),
    sa.Column('summary', sa.Text))

user_names_t = sa.Table(
    'user_names', metadata,
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', ondelete='CASCADE', name='user_names_id_fkey'),
              primary_key=True, autoincrement=False),
    sa.Column('title', sa.Text),
    sa.Column('first', sa.Text, nullable=False),
    sa.Column('middle', sa.Text),
    sa.Column('last', sa.Text, nullable=False),
    sa.Column('suffix', sa.Text),
    sa.Column('nickname', sa.Text),
    sa.UniqueConstraint('first', 'last'))

users_ts = sa.Table(
    'users_ts', metadata,
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', name='users_ts_article_id_fkey'),
              primary_key=True),
    sa.Column('tsvector', TSVECTOR, index=True, nullable=False))

articles_t = sa.Table(
    'articles', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('author_id', sa.Integer,
              sa.ForeignKey('users.id', name='articles_author_id_fkey'),
              nullable=False, index=True),
    sa.Column('published_by', sa.Integer,
              sa.ForeignKey('users.id', name='articles_published_by_fkey'),
              index=True),
    sa.Column('title', sa.Text, nullable=False, index=True),
    sa.Column('body', sa.Text, nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True)),
    sa.Column('updated_on', sa.DateTime(timezone=True)),
    sa.Column('is_published', sa.Boolean, nullable=False, default=False, server_default=sa.false()))

articles_ts = sa.Table(
    'articles_ts', metadata,
    sa.Column('article_id', sa.Integer,
              sa.ForeignKey('articles.id', name='articles_ts_article_id_fkey'),
              primary_key=True),
    sa.Column('tsvector', TSVECTOR, index=True, nullable=False))

comments_t = sa.Table(
    'comments', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('article_id', sa.Integer,
              sa.ForeignKey('articles.id', name='articles_article_id_fkey'),
              nullable=False, index=True),
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', name='articles_user_id_fkey'),
              nullable=False, index=True),
    sa.Column('body', sa.Text, nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True)),
    sa.Column('updated_on', sa.DateTime(timezone=True)))

replies_t = sa.Table(
    'replies', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', name='replies_user_id_fkey'),
              nullable=False, index=True),
    sa.Column('comment_id', sa.Integer,
              sa.ForeignKey('comments.id', name='replies_comment_id_fkey'),
              nullable=False, index=True),
    sa.Column('body', sa.Text, nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True)),
    sa.Column('updated_on', sa.DateTime(timezone=True)))

keywords_t = sa.Table(
    'keywords', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.Text, nullable=False))

article_keywords_t = sa.Table(
    'article_keywords', metadata,
    sa.Column('article_id', sa.Integer,
              sa.ForeignKey('articles.id', ondelete='CASCADE',
                            name='article_keywords_article_id_fkey')),
    sa.Column('keyword_id', sa.Integer,
              sa.ForeignKey('keywords.id', ondelete='CASCADE',
                            name='article_keywords_keyword_id_fkey')),
    sa.PrimaryKeyConstraint('article_id', 'keyword_id'))

article_read_access_t = sa.Table(
    'article_read_access', metadata,
    sa.Column('article_id', sa.Integer,
              sa.ForeignKey('articles.id', ondelete='CASCADE',
                            name='article_read_access_article_id_fkey')),
    sa.Column('user_id', sa.Integer,
              sa.ForeignKey('users.id', ondelete='CASCADE',
                            name='article_read_access_user_id_fkey')),
    sa.PrimaryKeyConstraint('article_id', 'user_id'))
