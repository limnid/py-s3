projects = {
    'test': {
        'name': 'Test project',
        'config_dir': '/var/www/test/.backup',
        'home_dir': '/var/www/test/public',
        'bucket': 'debug.lime',
        'exclude_dirs': {},
        'only_dirs': {},
        'commands': {
            'pull', 'push', 'init', 'rebase_digest'
        }
    },
}

databases = {
    'test': {
        'db_host': 'localhost',
        'db_user': 'user',
        'db_user_password': 'pass',
        'db_name': 'test',
        'backup_path': '/databases',
        'perm_path': '/databases'
    }
}

report_dirs = {
    '/test_dir/.backup/reports',
}
