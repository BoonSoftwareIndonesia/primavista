# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ActivityLog(models.Model):
    _name = 'api_ven.activity_log'
    _description = 'Activity Log'

    id = fields.Integer()
    user = fields.Integer('User ID')
    user_name = fields.Char('User')
    method = fields.Selection(
        [
            ('create', 'Create'), 
            ('write', 'Update'),
            ('unlink', 'Delete'),
        ]
    )
    model_id = fields.Char('Model')
    time_logged = fields.Datetime('Logging Time', default=fields.Datetime.now, required=True,)
    activity_log_line_ids = fields.One2many('api_ven.activity_log_line', 'activity_log_id', string="Log Lines")
    resource_id = fields.Integer('Resource ID')
    resource_name = fields.Char('Resource Name')
    
    def create_log_on_create(self, new_value, model_id):
        field_model = self.env['ir.model.fields']
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        for fname in new_value:
            field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])
            
            new_activity_log_line_value = {
                'field_label': str(field_desc['field_description']) if field_desc else "",
                'field_technical_name': fname,
                'new_value': new_value[fname],
                'activity_log_id': self.id
            }
            
            new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
    
    def create_log_on_write(self, new_value, old_value, model_id):
        field_model = self.env['ir.model.fields']
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        for fname in old_value:
            field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])
            
            new_activity_log_line_value = {
                'field_label': str(field_desc['field_description']) if field_desc else "",
                'field_technical_name': fname,
                'new_value': new_value[fname],
                'old_value': old_value[fname],
                'activity_log_id': self.id
            }
            
            new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
    
    def create_log_on_unlink(self, old_value, model_id):
        field_model = self.env['ir.model.fields']
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        for fname in old_value:
            field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])
            
            new_activity_log_line_value = {
                'field_label': str(field_desc['field_description']) if field_desc else "",
                'field_technical_name': fname,
                'old_value': old_value[fname],
                'activity_log_id': self.id
            }
            
            new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
