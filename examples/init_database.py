from odoo_tools.odoo import Environment

env = Environment()
env.context.init_logger = True

db = env.manage.db('test')
db.default_entrypoints()

env.manage.initialize_odoo()

db.init(['website', 'sale'], language='fr_CA', country='CA')
