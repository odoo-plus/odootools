import re


def fetch_db_version(cursor):
    query = "SELECT latest_version FROM ir_module_module WHERE name=%s"
    cursor.execute(query, ('base',))
    version = cursor.fetchone()

    if not version or not version[0]:
        return False
    else:
        return ".".join(version[0].split('.')[:2])


def get_tables(cursor, tables):
    query = """
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON (n.oid = c.relnamespace)
         WHERE c.relname IN %s
           AND c.relkind IN ('r', 'v', 'm')
           AND n.nspname = current_schema
    """
    cursor.execute(query, [tuple(tables)])
    return [row[0] for row in cursor.fetchall()]


def db_filter(dbs, dbfilter, hostname):
    if hostname:
        domain, _, rest = hostname.partition('.')

        if domain == 'www' and rest:
            domain = rest.partition('.')[0]

        domain, hostname = re.escape(domain), re.escape(hostname)
        rule = dbfilter.replace('%h', hostname).replace('%d', domain)
    else:
        rule = dbfilter.replace('%h', '.+').replace('%d', '.+')

    return [
        db
        for db in dbs
        if re.match(rule, db['name'])
    ]
