from jsonapi.db import MANY_TO_MANY
from jsonapi.db import MANY_TO_ONE
from jsonapi.db import ONE_TO_MANY
from jsonapi.db import ONE_TO_ONE
from jsonapi.model import Aggregate
from jsonapi.model import Derived
from jsonapi.model import Model
from jsonapi.model import Relationship
from jsonapi.tests.auth import current_user
from jsonapi.tests.db import *


class UserNameModel(Model):
    type_ = 'name'
    from_ = user_names_t
    fields = 'first', 'last', Derived('full', lambda rec: rec['first'] + ' ' + rec['last'])


class UserModel(Model):
    type_ = 'user'
    from_ = users_t

    fields = ('email', 'created_on', 'status',
              Relationship('name', 'UserNameModel',
                           ONE_TO_ONE, 'user_names_id_fkey'),
              Relationship('articles', 'ArticleModel',
                           ONE_TO_MANY, 'articles_author_id_fkey'),
              Aggregate('article_count', articles_t.c.id, sa.func.count))


class ArticleModel(Model):
    type_ = 'article'
    from_ = articles_t
    fields = ('title', 'body', 'created_on', 'updated_on', 'is_published',
              Relationship('author', 'UserModel',
                           MANY_TO_ONE, 'articles_author_id_fkey'),
              Relationship('keywords', 'KeywordModel',
                           MANY_TO_MANY, 'article_keywords_article_id_fkey'),
              Relationship('comments', 'CommentModel',
                           ONE_TO_MANY, 'articles_article_id_fkey'))
    access = sa.func.check_article_read_access
    user = current_user


class KeywordModel(Model):
    type_ = 'keyword'
    from_ = keywords_t
    fields = 'name'


class CommentModel(Model):
    type_ = 'comment'
    from_ = comments_t
    fields = ('body', 'created_on', 'updated_on',
              Relationship('author', 'UserModel', MANY_TO_ONE, 'articles_user_id_fkey'),
              Relationship('replies', 'ReplyModel', ONE_TO_MANY, 'replies_comment_id_fkey'))


class ReplyModel(Model):
    type_ = 'reply'
    from_ = replies_t
    fields = 'body', 'created_on', 'updated_on'
