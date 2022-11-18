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
                new_vals[rec.id] = {}
                
                for fname, fval in rec._fields.items():
                    new_vals[rec.id][fname] = fval.convert_to_read(
                        rec[fname], rec
                    )
            
#             raise UserError(str(new_vals))
            curr_rule = self.env['activity_log.rule'].search([('model', '=', self._name)])
            curr_rule.create_activity_logs(self._name, self.ids, new_vals = new_vals, method = "create")
                
            return new_records
        
        return None
            
    def _make_write(self):
        pass
    
    def _make_unlink(self):
        pass
    
    def create_activity_logs(self, new_records_ids, new_vals = {}, old_vals = {} method):
        activity_log_model = self.env['activity_log.activity_log']
        activity_log_line_model = self.env['activity_log.activity_log_line']
        model_model = self.env[self.model]
        
        for id in new_records_ids:
            new_activity_log_vals = {
                'method': method,
                'rule_id': self.id,
                'model': self.model
                'resouce_id': id
                'resource_name': model_model.browse(id).name_get()
            }
            
            new_log = activity_log_model.create(new_activity_log_vals)
        return None
    
    def _create_log_on_create(self):
        pass