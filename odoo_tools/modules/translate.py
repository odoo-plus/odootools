"""
Odoo Translation
================

This module has a collection of tools that can be used
to extract translations from Odoo. It needs a working instance of
Odoo to be able to import/export translations out of Odoo.

It can do some of the translation file generation on its own but
in order to prefill some already translated terms, it has to be able
to load them into odoo first.
"""
import re
import polib
import logging
from ..compat import Path
from datetime import datetime

_logger = logging.getLogger()


def get_modules(entry):
    try:
        match = re.match(r"(module[s]?): (.+)", entry.comment)
        _, modules = match.groups()
        modules = modules.split(',')
    except Exception:
        modules = []

    modules_lst = []
    for module in modules:
        module = module.strip()
        if module not in modules_lst:
            modules_lst.append(module)
    modules = tuple(modules_lst)
    return modules


def get_comments(entry):

    comments = [
        c
        for c in entry.comment.split('\n')
        if not c.startswith('module:')
        if not c.startswith('modules:')
    ]

    return comments


class PoFileReader(object):
    """ Iterate over po file to return Odoo translation entries """
    def __init__(self, source, options=None):

        if options is None:
            options = {
                "strict": False,
                "read_pot": False
            }

        def get_pot_path(source_name):
            # when fileobj is a TemporaryFile, its name is an inter in P3, a
            # string in P2
            if isinstance(source_name, str) and source_name.endswith('.po'):
                # Normally the path looks like /path/to/xxx/i18n/lang.po
                # and we try to find the corresponding
                # /path/to/xxx/i18n/xxx.pot file.
                # (Sometimes we have 'i18n_extra' instead of just 'i18n')
                path = Path(source_name)
                filename = path.parent.parent.name + '.pot'
                pot_path = path.with_name(filename)
                return pot_path.exists() and str(pot_path) or False
            return False

        # polib accepts a path or the file content as a string, not a fileobj
        if isinstance(source, str):
            self.pofile = polib.pofile(source)
            pot_path = get_pot_path(source)
        elif isinstance(source, polib.POFile):
            self.pofile = source
        else:
            # either a BufferedIOBase or result from NamedTemporaryFile
            self.pofile = polib.pofile(source.read().decode())
            pot_path = get_pot_path(source.name)

        if options.get('read_pot') and pot_path:
            # Make a reader for the POT file
            # (Because the POT comments are correct on GitHub but the
            # PO comments tends to be outdated. See LP bug 933496.)
            self.pofile.merge(polib.pofile(pot_path))

    def __iter__(self):
        for entry in self.pofile:
            if entry.obsolete:
                continue

            modules = get_modules(entry)
            comments = get_comments(entry)

            source = entry.msgid
            translation = entry.msgstr
            found_code_occurrence = False
            for occurrence, line_number in entry.occurrences:
                match = re.match(
                    r'(model|model_terms):([\w.]+),([\w]+):(\w+)\.([^ ]+)',
                    occurrence
                )
                if match:
                    type, model_name, field_name, module, xmlid = match.groups() # noqa

                    yield {
                        'type': type,
                        'imd_model': model_name,
                        'name': model_name+','+field_name,
                        'imd_name': xmlid,
                        'res_id': None,
                        'src': source,
                        'value': translation,
                        'comments': "\n".join(comments),
                        'module': modules,
                    }
                    continue

                match = re.match(r'(code):([\w/.]+)', occurrence)
                if match:
                    type, name = match.groups()
                    if found_code_occurrence:
                        # unicity constrain on code translation
                        continue
                    found_code_occurrence = True
                    yield {
                        'type': type,
                        'name': name,
                        'src': source,
                        'value': translation,
                        'comments': comments,
                        'res_id': int(line_number),
                        'module': modules,
                    }
                    continue

                match = re.match(r'(selection):([\w.]+),([\w]+)', occurrence)
                if match:
                    if self.options.get('strict'):
                        _logger.info(
                            "Skipped deprecated occurrence %s", occurrence
                        )
                        continue

                    type, model_name, name = match.groups()

                    yield {
                        'type': type,
                        'name': name,
                        'imd_model': model_name,
                        'res_id': int(line_number),
                        'src': source,
                        'value': translation,
                        'comments': comments,
                        'module': modules
                    }

                    continue

                match = re.match(
                    r'(sql_constraint|constraint):([\w.]+)', occurrence
                )
                if match:
                    _logger.info(
                        "Skipped deprecated occurrence %s", occurrence
                    )
                    continue
                _logger.error(
                    "malformed po file: unknown occurrence: %s", occurrence
                )


class PoFileWriter(object):
    """ Iterate over po file to return Odoo translation entries """
    def __init__(self, target, lang, pofile=None):

        self.buffer = target
        self.lang = lang
        if pofile is not None:
            self.po = pofile
        else:
            self.po = polib.POFile()

    def merge(self, pofile):
        self.po.merge(pofile)

    def write_rows(self, rows):
        # we now group the translations by source. That means one translation
        # per source.
        grouped_rows = {}
        modules = set([])

        for module, type, name, res_id, src, trad, comments in rows:
            row = grouped_rows.setdefault(src, {})
            row.setdefault('modules', set()).add(module)
            if not row.get('translation') and trad != src:
                row['translation'] = trad
            row.setdefault('tnrs', []).append((type, name, res_id))
            row.setdefault('comments', set()).update(comments)
            modules.add(module)

        for src, row in sorted(grouped_rows.items()):
            if not self.lang:
                # translation template, so no translation value
                row['translation'] = ''
            elif not row.get('translation'):
                row['translation'] = ''

            self.add_entry(
                row['modules'],
                sorted(row['tnrs']),
                src,
                row['translation'],
                row['comments']
            )

        self.write()

    def generate_header(self):
        import odoo.release as release

        modules = set([])

        self.po.header = (
            "Translation of %s.\n"
            "This file contains the translation of the following modules:"
            "\n%s"
        ) % (
            release.description, ''.join("\t* %s\n" % m for m in modules)
        )

    def generate_metadata(self):
        import odoo.release as release

        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M+0000')
        self.po.metadata = {
            'Project-Id-Version': "%s %s" % (
                release.description, release.version
            ),
            'Report-Msgid-Bugs-To': '',
            'POT-Creation-Date': now,
            'PO-Revision-Date': now,
            'Last-Translator': '',
            'Language-Team': '',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=UTF-8',
            'Content-Transfer-Encoding': '',
            'Plural-Forms': '',
        }

    def write(self):
        if not self.po.header:
            self.generate_header()
        if not self.po.metadata:
            self.generate_metadata()

        self.buffer.write(str(self.po).encode())

    def add_entry(self, modules, tnrs, source, trad, comments=None):
        entry = self.po.find(st=source)

        if not entry:
            entry = polib.POEntry(
                msgid=source,
                msgstr=trad,
            )
            self.po.append(entry)

        entry_modules = list(get_modules(entry))
        for module in modules:
            if module not in entry_modules:
                entry_modules.append(module)

        modules = entry_modules

        plural = len(modules) > 1 and 's' or ''
        entry.comment = "module%s: %s" % (plural, ', '.join(modules))

        if comments:
            entry_comments = get_comments(entry)
            for comment in comments:
                if comment not in entry_comments:
                    entry_comments.append(comment)
            comments = entry_comments

            entry.comment += "\n" + "\n".join(comments)

        code = False
        for typy, name, res_id in tnrs:
            if typy == 'code':
                code = True
            #     res_id = 0
            new_occurrence = None
            if isinstance(res_id, int) or res_id.isdigit():
                # second term of occurrence must be a digit
                # occurrence line at 0 are discarded when rendered to string
                new_occurrence = (u"%s:%s" % (typy, name), str(res_id))
            else:
                new_occurrence = (u"%s:%s:%s" % (typy, name, res_id), '')

            if new_occurrence not in entry.occurrences:
                entry.occurrences.append(new_occurrence)
        if code and "python-format" not in entry.flags:
            entry.flags.append("python-format")

        entry.flags = list(set(entry.flags))

    def add_entries(self, entries):
        for module, type, name, res_id, source, value, comments in entries:
            self.add_entry(
                modules=[module],
                tnrs=[
                    (type, name, res_id)
                ],
                source=source,
                trad=value,
                comments=comments
            )
