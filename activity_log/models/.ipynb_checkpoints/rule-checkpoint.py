from odoo import models, fields, api
from odoo.exceptions import UserError

class Rule(models.Model):
    _name = 'activity_log.rule'
    _description = 'Log Rule'

    id = fields.Integer()
    name = fields.Char('Name')
    user = fields.Integer('User ID')
    active = fields.Boolean(default = True)
    model = fields.Many2one(
        "ir.model",
        "Model",
        help="Select model for which you want to generate log.",
        ondelete="set null",
        index=True,
    )
    create_rule = fields.Boolean('Log Create', default = False)
    write_rule = fields.Boolean('Log Write', default = False)
    unlink_rule = fields.Boolean('Log Delete', default = False)
    time_created = fields.Datetime('Rule Created Time', default=fields.Datetime.now, required=True)
    activity_logs_ids = fields.One2many('activity_log.activity_log', 'rule_id', string='Logs')
    
    