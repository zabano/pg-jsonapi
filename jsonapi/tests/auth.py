from quart import g
from werkzeug.local import LocalProxy


class User:

    def __init__(self, user_id):
        self.id = int(user_id)


current_user = LocalProxy(lambda: g.get('user'))


def login(user_id):
    g.user = User(user_id)


def logout():
    g.user = None
