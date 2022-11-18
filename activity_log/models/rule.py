from odoo import models, fields, api
from odoo.exceptions import UserError

class Rule(models.Model):
    _name = 'activity_log.rule'
    _description = 'Log Rule'

    id = fields.Integer()
    name = fields.Char('Name')
    user = fields.Integer('User ID')
    active = fields.Boolean(default = True)
#     state = fields.Selection(
#         [("draft", "Draft"), ("subscribed", "Subscribed")],
#         required=True,
#         default="draft",
#     )
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
    
    @api.model
    def create(self, vals):
        if 'model' not in vals:
            raise UserError(_('No model is defined'))
        
        res = super.create(vals)
        
        if res.active:
            res._patch_methods()
        return res
    
    def _patch_methods(self):
#         Overwrite specified methods for the model
        if self.create_rule:
            self._make_create()
        if self.write_rule:
            self._make_write()
        if self.unlink_rule:
            self._make_unlink()

    def _make_create(self):
#         Patching a create method that will log its call
        self.ensure_one()
        
        @api.model_create_multi
        @api.returns("self", lambda value: value.id) # return record id?
        def create(self, vals_list, **kwargs):
            new_records = create.origin(self, vals_list, **kwargs)
            
            new_vals = {}
            for rec in new_records:
                for vals, rec in zip(vals_list, new_records):
                    new_vals[rec.id] = vals
            
            curr_rule = self.env['activity_log.rule'].search([('model', '=', self._name)])
            curr_rule.create_activity_logs(self._name, self.ids, "create",new_vals = new_vals)
                
            return new_records
        
        return create
            
    def _make_write(self):
        pass
    
    def _make_unlink(self):
        return None
    
    def create_activity_logs(self, new_records_ids, method, new_vals = {}, old_vals = {}):
        activity_log_model = self.env['activity_log.activity_log']
        model_model = self.env[self.model]
        
        for id in new_records_ids:
            new_activity_log_vals = {
                'method': method,
                'rule_id': self.id,
                'model': self.model,
                'resource_id': id,
                'resource_name': new_vals[id]['name']
            }
            
            new_log_id = activity_log_model.create(new_activity_log_vals)
            
            if method == 'create':
                self._create_log_on_create(new_vals[id])
            elif method == 'write':
                pass
            else:
                pass
            
        return None
    
    def _create_log_on_create(self, new_value):
        activity_log_line_model = self.env['activity_log.activity_log_line']
        
        for fname, fval in new_value:
            field_desc = field_model.search([('model_id', '=', self._name), ('name','=',fname)])
            
            activity_log_line_model.create({
                'field_label': str(field_desc['field_description']),
                'field_technical': fname,
                'new_value': str(fval)  
            })
        
        return None
    
    def deactive_rule(self):
        for rule in self:
            model_model = self.env[rule.model]
            for method in ["create", "write", "unlink"]:
                model_model._revert_method(method)
                    
        return self.write({'active':False})
            