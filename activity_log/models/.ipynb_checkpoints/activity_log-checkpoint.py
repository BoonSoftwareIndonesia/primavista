# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ActivityLog(models.Model):
    _name = 'activity_log.activity_log'
    _description = 'Activity Log'

    id = fields.Integer()
    user = fields.Integer('User ID')
    method = fields.Selection(
        [
            ('create', 'Create'), 
            ('write', 'Update'),
            ('unlink', 'Delete'),
        ]
    )
    model = fields.Char('Model')
    time_logged = fields.Datetime('Logging Time', default=fields.Datetime.now, required=True,)
    rule_id = fields.Many2one('activity_log.rule', string = "Origin")
    activity_log_line_ids = fields.One2many('activity_log.activity_log_line', 'activity_log_id', string="Log Lines")
    resource_id = fields.Integer('Resource ID')
    resource_name = fields.Char('Resource Name')