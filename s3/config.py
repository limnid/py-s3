import datetime

from pyramid.renderers import JSON


def configure_project(config):
    def datetime_adapter(obj, request):
        return obj.isoformat()

    json_renderer = JSON()
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    config.add_renderer('json', json_renderer)

    config.add_static_view('static', 'static', cache_max_age=0)

    from s3.routes import project_routes
    config.include(project_routes)
    config.add_tween('s3.tweens.timing_tween_factory')
