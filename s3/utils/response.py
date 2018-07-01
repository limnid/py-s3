class ResponseObject(object):
    def __init__(self, result):
        self.result = result

    def __json__(self, request):
        return self.result
