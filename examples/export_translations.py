from odoo_tools.odoo import Environment

env = Environment()
env.context.init_logger = True

db = env.manage.db('test')
db.default_entrypoints()

env.manage.initialize_odoo()

website = env.modules.get('website')
website.export_translations(db, ['fr_CA'])
