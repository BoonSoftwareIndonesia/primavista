from odoo import models, fields, api
import requests
from datetime import datetime
from odoo.http import request, Response
from odoo.exceptions import UserError

class PartnerExt(models.Model):
    _inherit = 'res.partner'
    
    name = fields.Char(index=True, required=True)
    x_studio_customer_id = fields.Char(string='Customer ID',copy=False)
    x_studio_customer_group = fields.Char(string='Customer Group',default='IOC')
    street = fields.Char(default='NA')
    zip = fields.Char(change_default=True,default='12345')
    city = fields.Char(default='NA')
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]",required=True)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=100)
    
    @api.constrains('x_studio_customer_id')
    def _check_x_studio_customer_id(self):
        for cust in self:
            if cust.x_studio_customer_id:
                is_duplicate = False
                is_duplicate = request.env['res.partner'].search([('id','!=',cust.id),('x_studio_customer_id', '=',cust.x_studio_customer_id)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + cust.x_studio_customer_id))
                    
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
            new_vals = self._format_data(vals_list, partners)
            # raise UserError(str(new_vals))
            self.create_activity_logs(partners, "create", new_vals = new_vals)
        return partners
    
    def _format_data(self, vals_list, new_records):
        new_vals = {}
        for rec in new_records:
            for vals, rec in zip(vals_list, new_records):
                new_vals[rec.id] = vals
        return new_vals
    
    
    def create_activity_logs(self, new_records, method, new_vals = {}, old_vals = {}):
        activity_log_model = self.env['api_ven.activity_log']
        model_model = self.env[self._name]
        
        for rec in new_records:
            new_activity_log_vals = {
                'method': method,
                'model_id': self._name,
                'resource_id': rec.id,
                'resource_name': new_vals[rec.id]['name']
            }

            new_log_id = activity_log_model.create(new_activity_log_vals)

            if method == 'create':
                new_log_id[0].create_log_on_create(new_vals[rec.id], self._name)
            elif method == 'write':
                pass
            else:
                pass
            
        return None
    
    def write(self,vals):
        res = super(PartnerExt, self).write(vals)
        
        if self.write_date != self.create_date:
            # the result of the super() is a bool, so we need to search for the product template object to pass to the api function
            partners = request.env['res.partner'].search([('id', '=', self.id)], limit=1)

            test_import = self._context.get('test_import')
            copy_context = self._context.get('copy_context')
            # if we are not testing and duplicating
            if not test_import and not copy_context:
                self.env['res.partner'].api_dw_customer(partners)
        return res
    