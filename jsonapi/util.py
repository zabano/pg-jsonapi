import re
import inflection

from jsonapi.exc import Error


class ArgumentParser:

    def __init__(self, args):
        """
        :param args: a dictionary representing the request query string
        :param include: an additional include value
        """

        self.include = dict()
        self.fields = dict()

        self.offset = 0
        self.limit = None

        #
        # include
        #

        if 'include' in args:
            for dot_path in args['include'].split(','):
                include = self.include
                for i, attr in enumerate(dot_path.split('.')):
                    if attr not in include:
                        include[attr] = dict()
                    include = include[attr]

        #
        # fields
        #

        for key, value in args.items():
            match = re.search('^fields\[([-_\w]+)\]$', key)
            if match:
                self.fields[match.group(1)] = set(inflection.underscore(x.lower()) for
                                                  x in value.split(',') + ['id'])

        #
        #   page
        #

        if 'page[size]' in args:

            try:
                self.limit = int(args['page[size]'])
            except ValueError:
                raise Error('page[size] request parameter must be an integer')

            if self.limit <= 0:
                raise Error('page[size] request parameter must be positive')

        if 'page[number]' in args and self.limit > 0:

            try:
                number = int(args['page[number]'])
            except ValueError:
                raise Error('page[number] request parameter must be an integer')
            else:
                if number <= 0:
                    raise Error('page[number] request parameter must be positive')
                self.offset = (number - 1) * self.limit
