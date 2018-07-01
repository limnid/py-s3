import time
from pyramid.settings import asbool
import logging

log = logging.getLogger(__name__)


def timing_tween_factory(handler, registry):
    if asbool(registry.settings.get('do_timing')):
        def timing_tween(request):
            start = time.time()
            try:
                response = handler(request)
            finally:
                end = time.time()
                log.debug('The request took %s seconds' % (end - start))
            return response

        return timing_tween
    return handler
