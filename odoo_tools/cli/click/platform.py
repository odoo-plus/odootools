import click
import platform as pp


@click.group(
    help="Print the platform name to the output."
)
@click.pass_context
def platform(ctx):
    pass


@platform.command()
@click.pass_context
def arch(ctx):
    arch = pp.processor()

    if arch == "x86_64":
        docker_arch = "amd64"
    elif arch == "aarch64":
        docker_arch = "arm64"
    else:
        docker_arch = arch

    print(docker_arch, end="")
