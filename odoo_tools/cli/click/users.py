import sys
import click
import json
from ast import literal_eval
from getpass import getpass
from password_strength import PasswordStats

from ...utils import random_string


@click.group()
def user():
    pass


@user.command("ls")
@click.option(
    '--internal',
    help="Internal User",
    is_flag=True,
    default=False
)
@click.option(
    '--shared',
    help="Shared User",
    is_flag=True,
    default=False
)
@click.option(
    '--inactive',
    help="Inactive user",
    is_flag=True,
    default=False
)
@click.option(
    '--domain',
    help="Custom domain"
)
@click.argument('db')
@click.pass_context
def list_users(ctx, internal, shared, inactive, domain, db):
    oenv = ctx.obj['env']

    cdb = oenv.manage.db(db)

    cdb.default_entrypoints()

    if domain:
        search_domain = literal_eval(domain)
    else:
        search_domain = []

    if internal:
        search_domain.append(['share', '=', False])

    if not internal and shared:
        search_domain.append(['share', '=', True])

    if inactive:
        search_domain.append(['active', '=', False])

    with cdb.env() as env:
        Users = env['res.users']

        users = Users.search(search_domain)

        for user in users:
            metadata = user.get_metadata()
            print(json.dumps({
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'xmlid': metadata[0]['xmlid']
            }))


@user.command("create")
@click.option(
    '--user-template',
    help="xmlid or id of the template",
)
@click.option(
    '--inactive',
    help="Set new user as inactive",
    is_flag=True,
    default=False
)
@click.argument("db")
@click.argument("login")
@click.argument("name")
@click.pass_context
def create_user(ctx, user_template, inactive, db, login, name):
    from odoo.exceptions import ValidationError
    oenv = ctx.obj['env']

    cdb = oenv.manage.db(db)

    cdb.default_entrypoints()

    with cdb.env() as env:
        Users = env['res.users']
        Config = env['ir.config_parameter']

        if not user_template:
            user_template_id = literal_eval(
                Config.get_param('base.template_portal_user_id', 'False')
            )
            user_template = Users.browse(user_template_id)
        else:
            if '.' in user_template:
                user_template = env.ref(user_template)
            else:
                user_template_id = int(user_template)
                user_template = Users.browse(user_template_id)

        vals = {
            "login": login,
            "name": name,
            "active": True
        }

        if inactive:
            vals['active'] = False

        try:
            user = user_template.with_context(no_reset_password=True).copy(
                vals
            )
            metadata = user.get_metadata()
            print(json.dumps({
                "id": user.id,
                "name": user.name,
                "login": user.login,
                "xmlid": metadata[0]['xmlid']
            }))

        except ValidationError as exc:
            print(exc.name)
            sys.exit(1)


@user.command('reset-pw')
@click.option(
    '--auto',
    help="Auto generate password and output it.",
    is_flag=True,
    default=False
)
@click.option(
    '--no-password',
    help="Remove password",
    is_flag=True,
    default=False
)
@click.option(
    '--no-password-policy',
    help="Do not check password strength",
    is_flag=True,
    default=False
)
@click.argument('db')
@click.argument('login')
@click.pass_context
def reset_pw_user(ctx, auto, no_password, no_password_policy, db, login):
    oenv = ctx.obj['env']

    if no_password:
        new_password = ''
    elif auto:
        new_password = random_string(20)
    else:
        new_password = getpass()
        new_password2 = getpass("Repeat password: ")

        if new_password != new_password2:
            print("Passwords do no match, try again.")
            sys.exit(1)

        if not no_password_policy:
            stats = PasswordStats(new_password)
            if stats.strength() < 0.66:
                print("Password not strong enough.")
                sys.exit(1)

    cdb = oenv.manage.db(db)
    cdb.default_entrypoints()
    with cdb.env() as env:
        Users = env['res.users']

        user = Users.with_context(active_test=False).search(
            [['login', '=', login]], limit=1
        )

        user.password = new_password

    if auto:
        print("Setting new password to: {}".format(new_password))


@user.command("remove")
@click.option(
    '--soft',
    help="Mark user as inactive",
    is_flag=True,
    default=False
)
@click.argument("db")
@click.argument("login")
@click.pass_context
def remove_user(ctx, soft, db, login):
    oenv = ctx.obj['env']
    cdb = oenv.manage.db(db)

    cdb.default_entrypoints()

    with cdb.env() as env:
        Users = env['res.users']

        user = Users.with_context(active_test=False).search(
            [['login', '=', login]], limit=1
        )

        if not user:
            print("Nothing to do!")
            sys.exit(0)

        if not soft:
            user.unlink()
        elif user.active:
            user.toggle_active()

        print("Done!")
