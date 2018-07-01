from pyramid.config import Configurator
from pyramid.settings import asbool

from s3.tweens import timing_tween_factory


def fix_dict(string):
    return [x.strip() for x in string.split(',')]


def main(global_config, **settings):
    production_deployment = asbool(settings.get('production_deployment', 'false'))
    settings['production_deployment'] = production_deployment
    settings['sparkpost_url'] = settings.get('sparkpost.url')
    settings['sparkpost_from'] = settings.get('sparkpost.from')
    settings['sparkpost_subject'] = settings.get('sparkpost.subject')
    settings['sparkpost_subject'] = settings.get('sparkpost.subject')
    settings['sparkpost_reply_to'] = settings.get('sparkpost.reply_to')
    settings['sparkpost_token'] = settings.get('sparkpost.token')

    configurator = Configurator(settings=settings)

    from s3.config import configure_project
    configurator.include(configure_project)
    configurator.scan()

    return configurator.make_wsgi_app()
