import click


@click.group()
def config():
    pass


@config.command("set")
@click.option('-s', '--section', default='options')
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_value(ctx, section, key, value):
    env = ctx.obj['env']

    with env.config() as config:
        config.set(section, key, value)


@config.command("get")
@click.option('-s', '--section', default='options')
@click.argument('key')
@click.pass_context
def get_value(ctx, section, key):
    env = ctx.obj['env']

    with env.config() as config:
        print(config.get(section, key))


@config.command("ls")
@click.pass_context
def list_values(ctx):
    env = ctx.obj['env']

    with env.config() as config:
        for key, value in config._sections.items():
            for key2, value in value.items():
                print("{}.{} = {}".format(key, key2, value))
