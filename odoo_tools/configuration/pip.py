import sys


def pip_command(user=None, target=None, upgrade=False):
    base_install_args = [
        sys.executable,
        '-m',
        'pip',
        'install',
    ]

    args = []
    if user is True:
        args.append('--user')

    if target is not None:
        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )
        args += [
            "--target", str(target),
            "--implementation", "cp",
            "--python", python_version,
            # "--only-binary", ":all:"
            "--no-deps",
        ]

    if upgrade:
        args.append('-U')

    return base_install_args + args
