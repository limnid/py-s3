import fnmatch
import os
import time
import zipfile
from os.path import basename

from pyramid.httpexceptions import HTTPError
from pyramid.view import view_config

from s3.projects import projects, report_dirs, databases
from s3.utils.backup import BackupManager
from s3.utils.backup import LocalBackup
from s3.utils.backup import S3Backup
from s3.utils.mailer import send_report, write_report, view_reports
from s3.utils.response import ResponseObject


@view_config(route_name='backup', renderer='json')
def main_view(request):
    project_name = request.matchdict['project']
    command_name = request.matchdict['command']

    # if project exists
    project_name = project_name if project_name in list(projects.keys()) else None
    if not project_name:
        return

    # if command exists
    project = projects.get(project_name)
    command_name = command_name if command_name in list(project.get('commands')) else None
    if not command_name:
        return

    home_dir = project.get('home_dir')
    bucket = project.get('bucket')
    config_dir = project.get('config_dir')
    exclude_dirs = project.get('exclude_dirs')
    only_dirs = project.get('only_dirs')

    # Worker
    job = LocalBackup(
        ConfigDir=config_dir,
        HomeDir=home_dir)

    if job.is_lock():
        return

    # Local cache
    local = LocalBackup(
        HomeDir=home_dir,
        ConfigDir=config_dir,
        ExcludeDirs=exclude_dirs,
        OnlyDirs=only_dirs)
    local.sync()

    # S3 backup
    s3 = S3Backup(
        S3Bucket=bucket,
        HomeDir=home_dir,
        ConfigDir=config_dir,
        ExcludeDirs=exclude_dirs,
        OnlyDirs=only_dirs)
    s3.sync()

    manager = BackupManager()
    manager.slave = local
    manager.master = s3

    commands = {
        'pull': lambda m: m.pull(),
        'push': lambda m: m.push(),
        'init': lambda m: m.init(),
        'rebase_digest': lambda m: m.rebase_digest(),
    }
    commands[command_name](manager)

    # Lock job
    job.lock()

    # Apply changes
    result = manager.apply()

    if result:
        # send_mail(request, '%s backup success' % project.get('name'), result)
        write_report(request, job.reports_dir, project.get('name'), {
            'count': result['count'],
            'size': result['size'],
            'date': result['date'],
            'project': project.get('name')
        })

    # Unlock job
    job.unlock()

    return ResponseObject({
        'message': 'OK'
    })


@view_config(route_name='report', renderer='json')
def report_view(request):
    send_report(request, report_dirs)


@view_config(route_name='reports', renderer='json')
def reports_view(request):
    print(view_reports(request, report_dirs))


@view_config(route_name='dump', renderer='json')
def dump_view(request):
    project_name = request.matchdict['project']

    # if project exists
    project_name = project_name if project_name in list(databases.keys()) else None
    if not project_name:
        return

    project = databases.get(project_name)

    # Getting current datetime to create seprate backup folder like "12012013-071334".
    DATETIME = time.strftime('%m_%d_%Y___%H_%M_%S')

    TODAYBACKUPPATH = project.get('backup_path') + DATETIME

    # Checking if backup folder already exists or not. If not exists will create it.
    # print("creating backup folder")

    if not os.path.exists(TODAYBACKUPPATH):
        os.makedirs(TODAYBACKUPPATH)

    db = project.get('db_name')
    path = TODAYBACKUPPATH + "/" + db
    dumpcmd = "mysqldump" \
              " -u " + project.get('db_user') + \
              " -p" + project.get('db_user_password') + \
              " " + db + \
              " > " + path + ".sql"
    os.system(dumpcmd)

    try:
        import zlib
        mode = zipfile.ZIP_DEFLATED
    except:
        mode = zipfile.ZIP_STORED

    zf = zipfile.ZipFile(path + '.zip', 'w', mode)
    zf.write(path + ".sql")
    zf.close()

    os.remove(path + ".sql")


@view_config(route_name='zip_sql', renderer='json')
def zip_view(request):
    project_name = request.matchdict['project']

    # if project exists
    project_name = project_name if project_name in list(projects.keys()) else None
    if not project_name:
        return

    project = projects.get(project_name)
    home_dir = project['home_dir']

    if not os.path.exists(home_dir):
        os.makedirs(home_dir)

    matches = []
    for root, dirnames, filenames in os.walk(home_dir):
        for filename in fnmatch.filter(filenames, '*.sql'):
            matches.append(os.path.join(root, filename))

    try:
        import zlib
        mode = zipfile.ZIP_DEFLATED
    except:
        mode = zipfile.ZIP_STORED

    for path in matches:
        zf = zipfile.ZipFile(path + '.zip', 'w', mode)
        zf.write(path, basename(path))
        zf.close()
        os.remove(path)

    return ResponseObject({
        'message': 'OK'
    })


@view_config(route_name='status', renderer='json')
def status_view(request):
    return ResponseObject({
        'message': 'OK',
        'projects': len(projects),
        'databases': len(databases),
    })


@view_config(context=HTTPError, renderer='json')
def error_view(exc, request):
    return ResponseObject({
        'message': exc.title,
    })
