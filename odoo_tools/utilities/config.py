from pathlib import Path

v15_options = {
    'ODOO_CONFIG': ('config', None),
    'ODOO_SAVE': ('save', None),
    'ODOO_INIT': ('init', None),
    'ODOO_UPDATE': ('update', None),
    'ODOO_WITHOUT_DEMO': ('without_demo', False),
    'ODOO_IMPORT_PARTIAL': ('import_partial', ''),
    'ODOO_PIDFILE': ('pidfile', None),
    'ODOO_ADDONS_PATH': ('addons_path', None),
    'ODOO_UPGRADE_PATH': ('upgrade_path', None),
    'ODOO_LOAD': ('server_wide_modules', 'base,web'),
    'ODOO_DATA_DIR': ('data_dir', str(Path.home() / '.local/share/Odoo')),
    'ODOO_HTTP_INTERFACE': ('http_interface', ''),
    'ODOO_HTTP_PORT': ('http_port', 8069),
    'ODOO_LONGPOLLING_PORT': ('longpolling_port', 8072),
    'ODOO_NO_HTTP': ('http_enable', True),
    'ODOO_PROXY_MODE': ('proxy_mode', False),
    'ODOO_DB_FILTER': ('dbfilter', ''),
    'ODOO_TEST_FILE': ('test_file', False),
    'ODOO_TEST_ENABLE': ('test_enable', None),
    'ODOO_TEST_TAGS': ('test_tags', None),
    'ODOO_SCREENCASTS': ('screencasts', None),
    'ODOO_SCREENSHOTS': ('screenshots', str(Path("/tmp") / 'screenshots')),
    'ODOO_LOGFILE': ('logfile', None),
    'ODOO_SYSLOG': ('syslog', False),
    'ODOO_LOG_HANDLER': ('log_handler', ':INFO'),
    'ODOO_LOG_DB': ('log_db', False),
    'ODOO_LOG_DB_LEVEL': ('log_db_level', 'warning'),
    'ODOO_LOG_LEVEL': ('log_level', 'info'),
    'ODOO_EMAIL_FROM': ('email_from', False),
    'ODOO_FROM_FILTER': ('from_filter', False),
    'ODOO_SMTP': ('smtp_server', 'localhost'),
    'ODOO_SMTP_PORT': ('smtp_port', 25),
    'ODOO_SMTP_SSL': ('smtp_ssl', False),
    'ODOO_SMTP_USER': ('smtp_user', False),
    'ODOO_SMTP_PASSWORD': ('smtp_password', False),
    'ODOO_SMTP_SSL_CERTIFICATE_FILENAME': (
        'smtp_ssl_certificate_filename', False
    ),
    'ODOO_SMTP_SSL_PRIVATE_KEY_FILENAME': (
        'smtp_ssl_private_key_filename', False
    ),
    'ODOO_DATABASE': ('db_name', False),
    'ODOO_DB_USER': ('db_user', False),
    'ODOO_DB_PASSWORD': ('db_password', False),
    'ODOO_PG_PATH': ('pg_path', None),
    'ODOO_DB_HOST': ('db_host', False),
    'ODOO_DB_PORT': ('db_port', False),
    'ODOO_DB_SSLMODE': ('db_sslmode', 'prefer'),
    'ODOO_DB_MAXCONN': ('db_maxconn', 64),
    'ODOO_DB_TEMPLATE': ('db_template', 'template0'),
    'ODOO_LOAD_LANGUAGE': ('load_language', None),
    'ODOO_LANGUAGE': ('language', None),
    'ODOO_I18N_EXPORT': ('translate_out', None),
    'ODOO_I18N_IMPORT': ('translate_in', None),
    'ODOO_I18N_OVERWRITE': ('overwrite_existing_translations', False),
    'ODOO_MODULES': ('translate_modules', None),
    'ODOO_NO_DATABASE_LIST': ('list_db', True),
    'ODOO_DEV': ('dev_mode', None),
    'ODOO_SHELL_INTERFACE': ('shell_interface', None),
    'ODOO_STOP_AFTER_INIT': ('stop_after_init', False),
    'ODOO_OSV_MEMORY_COUNT_LIMIT': ('osv_memory_count_limit', False),
    'ODOO_TRANSIENT_AGE_LIMIT': ('transient_age_limit', 1.0),
    'ODOO_OSV_MEMORY_AGE_LIMIT': ('osv_memory_age_limit', False),
    'ODOO_MAX_CRON_THREADS': ('max_cron_threads', 2),
    'ODOO_UNACCENT': ('unaccent', False),
    'ODOO_GEOIP_DB': ('geoip_database', '/usr/share/GeoIP/GeoLite2-City.mmdb'),
    'ODOO_WORKERS': ('workers', 0),
    'ODOO_LIMIT_MEMORY_SOFT': ('limit_memory_soft', 2147483648),
    'ODOO_LIMIT_MEMORY_HARD': ('limit_memory_hard', 2684354560),
    'ODOO_LIMIT_TIME_CPU': ('limit_time_cpu', 60),
    'ODOO_LIMIT_TIME_REAL': ('limit_time_real', 120),
    'ODOO_LIMIT_TIME_REAL_CRON': ('limit_time_real_cron', -1),
    'ODOO_LIMIT_REQUEST': ('limit_request', 8192)
}


options = {
    15: v15_options
}

outdated_options_map = {
    15: {
        'xmlrpc_port': 'http_port',
        'xmlrpc_interface': 'http_interface',
        'xmlrpc': 'http_enable',
    }
}

custom_env_params = {
    'MASTER_PASSWORD': ('admin_passwd', None)
}


def get_odoo_casts(env):
    config = env.odoo_config()

    return {
        val.get_opt_string().replace('--', 'ODOO_').replace('-', '_').upper():
            (key, val.my_default)
        for key, val in config.casts.items()
    }


def get_env_params(env, odoo_version):
    if odoo_version not in options:
        opts = get_odoo_casts(env)
    else:
        opts = options[odoo_version].copy()

    opts.update(custom_env_params)

    return opts


def parse_value(value):
    if value == 'True' or value == 'true':
        value = True
    if value == 'False' or value == 'false':
        value = False
    if value == 'None':
        value = None

    return value


def get_defaults(params):
    return {
        val[0]: val[1]
        for val in params.values()
    }
