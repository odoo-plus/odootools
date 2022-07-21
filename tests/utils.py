from odoo_tools.api.objects import Manifest


def generate_odoo_dir(tmp_path):
    odoo_dir = tmp_path / "odoo"
    odoo_dir.mkdir()
    addons_dir = odoo_dir / "addons"
    addons_dir.mkdir()

    return odoo_dir, addons_dir


def generate_addons(addons_dir, modules, **kw):
    for module in modules:
        mod_dir = addons_dir / module
        mod_dir.mkdir()

        manifest = mod_dir / '__manifest__.py'

        with manifest.open('w') as man:
            module_dict = {
                "description": module,
                "depends": ["web"]
            }

            for key, value in kw.items():
                module_dict[key] = value

            man.write(repr(module_dict))


def generate_files(current_folder, files):
    current_folder.mkdir(exist_ok=True, parents=True)

    for key, value in files.items():
        if isinstance(value, dict):
            generate_files(current_folder / key, value)
        else:
            cur_file = current_folder / key
            with cur_file.open("w") as fout:
                fout.write(value)


def generate_addons_full(addons_dir, module, manifest, files):
    module_path = addons_dir / module

    module_path.mkdir(exist_ok=True, parents=True)

    man = Manifest(
        module_path,
        manifest
    )
    man._manifest = man.path / '__manifest__.py'

    man.save()

    generate_files(man.path, files)
