# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ActivityLogLine(models.Model):
    _name = 'activity_log.activity_log_line'
    _description = 'Activity Log Line'

    id = fields.Integer()
    field_label = fields.Char('Field')
    field_technical_name = fields.Char('Technical Name')
    activity_log_id = fields.Many2one('activity_log.activity_log')
    old_value = fields.Char('Old Value')
    new_value = fields.Char('New Value')
    