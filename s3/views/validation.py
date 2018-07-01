from pyramid.response import Response
from pyramid.view import view_config


class ValidationFailure(Exception):
    def __init__(self, msg):
        self.msg = msg


@view_config(context=ValidationFailure)
def failed_validation(exc, request):
    response = Response('Failed validation: %s' % exc.msg)
    response.status_int = 500
    return response
