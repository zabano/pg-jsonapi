class Error(Exception):

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ModelError(Error):

    def __init__(self, message, model):
        super().__init__(message)
        self.model = model

    def __str__(self):
        return '[{}] {}'.format(self.model.name, self.message)


class APIError(ModelError):

    def __init__(self, message, model, status=400):
        super().__init__(message, model)
        self.status = status


class LargeResult(APIError):
    def __init__(self, message, model, size, limit):
        super().__init__(message, model, 400)
        self.size = size
        self.limit = limit


class DataTypeError(Error):

    def __init__(self, message, data_type):
        super().__init__(message)
        self.data_type = data_type

    def __str__(self):
        return '{} {}'.format(self.data_type, self.message)


class NotFound(APIError):

    def __init__(self, object_id, model):
        message = "object not found: {}({})".format(model.type_, object_id)
        super().__init__(message, model, 404)
        self.object_id = object_id


class Forbidden(APIError):

    def __init__(self, object_id, model):
        message = "access denied for: {}({})".format(model.type_, object_id)
        super().__init__(message, model, 403)
        self.object_id = object_id
