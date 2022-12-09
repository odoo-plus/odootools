class OdooVersionedString(object):

    def __init__(self, template):
        self.template = template
        self.data = None

    def get_string(self):
        from odoo.release import version_info
        return self.template.format(version_info=version_info)

    def __str__(self):
        if not self.data:
            self.data = self.get_string()
        return self.data

    def __eq__(self, other):
        return self.template == other.template
