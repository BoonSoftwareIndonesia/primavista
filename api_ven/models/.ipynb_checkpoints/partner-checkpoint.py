from odoo import models, fields, api
import requests
from datetime import datetime
from odoo.http import request, Response
from odoo.exceptions import UserError

class PartnerExt(models.Model):
    _inherit = 'res.partner'
    
    # override fields
    name = fields.Char(index=True, required=True)
    x_studio_customer_id = fields.Char(string='Customer ID',copy=False)
    x_studio_customer_group = fields.Char(string='Customer Group',default='IOC')
    street = fields.Char(default='NA')
    zip = fields.Char(change_default=True,default='12345')
    city = fields.Char(default='NA')
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]",required=True)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=100)
    
    # constraints to check for duplicate x_studio_customer_id
    @api.constrains('x_studio_customer_id')
    def _check_x_studio_customer_id(self):
        for cust in self:
            if cust.x_studio_customer_id:
                is_duplicate = False
                is_duplicate = request.env['res.partner'].search([('id','!=',cust.id),('x_studio_customer_id', '=',cust.x_studio_customer_id)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + cust.x_studio_customer_id))
    
    # set copy context if duplicating existing partner
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if 'copy_context' not in self._context:
            res = super(PartnerExt, self).with_context(copy_context=True).copy(default=default)
        else:
            res = super(PartnerExt, self).copy(default=default)
        return res
    
    # function to set default value if null
    def set_default(self,partners):
        if not partners.x_studio_customer_group:
            partners.x_studio_customer_group = "IOC"
        if not partners.street:
            partners.street = "NA"
        if not partners.city:
            partners.city = "NA"
        if not partners.zip:
            partners.zip = "12345"
        if not partners.country_id:
            partners.country_id = 100
    
    # triggers the api dw product function that sends an api log when a customer is created 
    @api.model_create_multi
    def create(self, vals_list):
        
        # validation, internal reference and state cannot be null if we are not duplicating
        if not self._context.get('copy_context'):
            if vals_list[0]['x_studio_customer_id'] is False:
                raise UserError(('Internal reference cannot be null (partner-create)'))
                
            if vals_list[0]['state_id'] is False:
                raise UserError(('State cannot be null (partner-create)'))
                
        partners = super(PartnerExt, self).create(vals_list)
        
        self.set_default(partners)
        
        # only send the data when we click import and not test
        test_import = self._context.get('test_import')
        if not test_import:
            self.env['res.partner'].api_dw_customer(partners)
            
            new_vals = {}
            for rec in partners:
                for vals, rec in zip(vals_list, partners):
                    new_vals[rec.id] = vals
                    
            # create activity log for partner creation
            self.create_activity_logs(partners, "create", new_vals = new_vals)
        return partners
    
    def create_activity_logs(self, new_records, method, new_vals = {}, old_vals = {}):
        activity_log_model = self.env['api_ven.activity_log']
        model_model = self.env[self._name]
        
        curr_user_id = self._context
        curr_user_id = curr_user_id.get('uid')
        curr_user_name = self.env['res.users'].browse(curr_user_id)
        
        # format_string = f"New values = {str(new_vals)} \n Old values = {str(old_vals)} \n Records = id:{str(new_records['id'])}, name:{str(new_records['name'])}"
        
        for rec in new_records:
            new_activity_log_vals = {
                'method': method,
                'user':curr_user_id,
                'user_name':curr_user_name[0].name,
                'model_id': self._name,
                'resource_id': rec['id'],
                'resource_name': rec['name']
            }

            # create activity log
            new_log_id = activity_log_model.create(new_activity_log_vals)

            # create the activity log line for the activity log
            if method == 'create':
                new_log_id[0].create_log_on_create(new_vals[rec['id']], self._name)
            elif method == 'write':
                new_log_id[0].create_log_on_write(new_vals[rec['id']], old_vals[rec['id']],self._name)
                pass
            else:
                new_log_id[0].create_log_on_unlink(old_vals[rec['id']], self._name)
            
        return None
    
    def write(self,vals):
        # get the old vals
        old_vals = {
                rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())
        }
                
        res = super(PartnerExt, self).write(vals)
        
        if self.write_date != self.create_date:
            # the result of the super() is a bool, so we need to search for the partner to pass to the api function
            partners = request.env['res.partner'].search([('id', '=', self.id)], limit=1)

            test_import = self._context.get('test_import')
            copy_context = self._context.get('copy_context')
            
            # if we are not testing and duplicating, send api
            if not test_import and not copy_context:
                # get new vals
                new_vals = {rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())}
                # create activity log for partner update
                self.create_activity_logs(self, "write", new_vals=new_vals, old_vals=old_vals)
                # send api 
                self.env['res.partner'].api_dw_customer(partners)
        return res
    
    @api.ondelete(at_uninstall=False)
    def _unlink_except_user(self):
        old_vals = {}
        records = []
        
        for rec in self:
            # get old vals
            old_vals[rec.id] = {
                'x_studio_customer_id': "" if not rec.x_studio_customer_id else rec.x_studio_customer_id, 
                'name': "" if not rec.name else rec.name, 
                'x_studio_customer_group': "" if not rec.x_studio_customer_group else rec.x_studio_customer_group, 
                'street': "" if not rec.street else rec.street, 
                'city': "" if not rec.city else rec.city, 
                'state_id': "" if not rec.state_id.name else rec.state_id.name, 
                'zip': "" if not rec.zip else rec.zip, 
                'country_id': "" if not rec.country_id.name else rec.country_id.name
            }
            records.append({'id': rec.id, 'name': rec.name})
        
        super(PartnerExt, self)._unlink_except_user()
        # create activity log for partner deletion
        self.create_activity_logs(records, "unlink" , old_vals = old_vals)
        
        return None
    