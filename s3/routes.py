def project_routes(config):
    config.add_route('backup', '/backup/{project}/{command}')
    config.add_route('dump', '/dump/{project}')
    config.add_route('zip_sql', '/zip_sql/{project}')
    config.add_route('report', '/report/{command}')
    config.add_route('reports', '/reports')
    config.add_route('status', '/status')
