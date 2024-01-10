# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ActivityLog(models.Model):
    _name = 'api_ven.activity_log'
    _description = 'Activity Log'

    # Activity log model's fields =============================
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
    
    
    
    # Method to create activity log lines for record creation =============================
    def create_log_on_create(self, new_value, model_id):
        # Assign the fields model to a variable
        field_model = self.env['ir.model.fields']
        # Assign the activity_log_line model to a variable
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        # Loop through the record's new_value
        for fname in new_value:
            # Search for the current field's label based on its technical name and model which it belongs to
            field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])
            
            # Declare the values for the activity log line's fields
            new_activity_log_line_value = {
                'field_label': str(field_desc['field_description']) if field_desc else "",
                'field_technical_name': fname,
                'new_value': 'False' if ((type(new_value[fname]) == bool) and new_value[fname] is False) else new_value[fname],
                'activity_log_id': self.id
            }
            
            # Create activity log line
            new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
    
    
    
    # Method to create activity log lines for record update =============================
    def create_log_on_write(self, new_value, old_value, model_id):
        # Assign the fields model to a variable
        field_model = self.env['ir.model.fields']
        # Assign the activity_log_line model to a variable 
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        # Loop through the record's new_value
        for fname in old_value:
            # If the current field is not "id", create an activity log line
            # Since the value of id cannot change, we don't have to create an activity log line for it
            # because the new value will always be blank and would cause an error
            if fname != "id":
                # Search for the current field's label based on its technical name and model which it belongs to
                field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])

                # Declare the values for the activity log line's fields
                new_activity_log_line_value = {
                    'field_label': str(field_desc['field_description']) if field_desc else "",
                    'field_technical_name': fname,
                    'new_value': 'False' if ((type(new_value[fname]) == bool) and new_value[fname] is False) else new_value[fname],
                    'old_value': 'False' if ((type(old_value[fname]) == bool) and old_value[fname] is False) else old_value[fname],
                    'activity_log_id': self.id
                }

                # Create activity log line
                new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
    
    
    
    # Method to create activity log lines for record deletion =============================
    def create_log_on_unlink(self, old_value, model_id):
        # Assign the fields model to a variable
        field_model = self.env['ir.model.fields']
        # Assign the activity_log_line model to a variable 
        activity_log_line_model = self.env['api_ven.activity_log_line']
        
        for fname in old_value:
            # Search for the current field's label based on its technical name and model which it belongs to
            field_desc = field_model.search([('model_id', '=', model_id), ('name','=',fname)])
            
            # Declare the values for the activity log line's fields
            new_activity_log_line_value = {
                'field_label': str(field_desc['field_description']) if field_desc else "",
                'field_technical_name': fname,
                'old_value': 'False' if ((type(old_value[fname]) == bool) and old_value[fname] is False) else old_value[fname],
                'activity_log_id': self.id
            }
            
            # Create activity log line
            new_records = activity_log_line_model.create(new_activity_log_line_value)
        return new_records
