import json
import os

import requests
from pyramid.renderers import render

from s3 import projects
from s3.utils import FileUtils


def write_report(request, report_dir, name, values):
    utils = FileUtils()
    result = render('s3:templates/mail_report.pt', values, request=request)
    utils.file_create(report_dir, name, result, True)


def send_report(request, paths):
    utils = FileUtils()
    files = []
    for dir_path in paths:
        files = files + utils.scan_dir(dir_path, [], [])

    contents = []
    for file in files:
        content = utils.file_open(file, True)
        if content:
            os.remove(file)
            contents.append(content)

    if len(contents) > 0:
        content = ' '.join(contents)
        result = render('s3:templates/mail_base.pt', {}, request=request)
        result = result.replace('{project_count}', str(len(projects.projects) - 1))
        result = result.replace('{edited_count}', str(len(contents)))
        result = result.replace('{content}', content)
        send_mail(request, 'Backup report', result)


def view_reports(request, paths):
    utils = FileUtils()
    files = []
    for dir_path in paths:
        files = files + utils.scan_dir(dir_path, [], [])

    contents = []
    for file in files:
        content = utils.file_open(file, True)
        if content:
            contents.append(content)

    if len(contents) > 0:
        content = ' '.join(contents)
        result = render('s3:templates/mail_base.pt', {}, request=request)
        result = result.replace('{project_count}', str(len(projects.projects) - 1))
        result = result.replace('{edited_count}', str(len(contents)))
        result = result.replace('{content}', content)
        return result


def send_mail(request, subject, html):
    settings = request.registry.settings
    headers = {
        'Content-Type': 'application/json',
        'Authorization': settings['sparkpost_token'],
    }
    data = {
        'content': {
            'from': settings['sparkpost_from'],
            'subject': subject,
            'reply_to': settings['sparkpost_reply_to'],
            'html': html,
        },
        'recipients': [
            {'address': 'codes.fusion@gmail.com'},
            {'address': 'suren@afishamedia.net'},
        ],
        'open_tracking': False,
        'click_tracking': False
    }
    response = requests.post(settings['sparkpost_url'], data=json.dumps(data), headers=headers)
