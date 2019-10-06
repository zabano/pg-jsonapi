from werkzeug.local import LocalProxy

g = dict()
current_user = LocalProxy(lambda: g.get('user'))


class User:

    def __init__(self, user_id):
        self.id = int(user_id)


def login(user_id):
    g['user'] = User(user_id)


def logout():
    g['user'] = None
