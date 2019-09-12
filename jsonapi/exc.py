class Error(Exception):
    """ Generic error """


class ModelError(Error):
    def __init__(self, message, model):
        super().__init__('[{}] {}'.format(model.name, message))
