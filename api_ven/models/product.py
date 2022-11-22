from odoo import models, fields, api
from odoo.http import request, Response
from odoo.exceptions import UserError
from datetime import datetime

class ProductTemplateExt(models.Model):
    _inherit = 'product.template'
    
    default_code = fields.Char(
        'Internal Reference', 
        compute='_compute_default_code',
        inverse='_set_default_code', 
        store=True, 
        required=True)
    
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.template'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + product_tmpl.default_code))
                    
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if 'copy_context' not in self._context:
            res = super(ProductTemplateExt, self).with_context(copy_context=True).copy(default=default)
        else:
            res = super(ProductTemplateExt, self).copy(default=default)
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
#         raise UserError((vals_list))
        if not self._context.get('copy_context'):
            if vals_list[0]['default_code'] is False:
                raise UserError(('Internal reference cannot be null (product template-create)'))
            if vals_list[0]['standard_price'] is False:
                raise UserError(('Cost cannot be null (product template-create)'))
        
        products = super(ProductTemplateExt, self).create(vals_list)
        
        # check the context, if it is not a test, then send api log to wms
        test_import = self._context.get('test_import')
        if not test_import:
            new_vals = {}
            for rec in products:
                for vals, rec in zip(vals_list, products):
                    new_vals[rec.id] = vals
            
            self.create_activity_logs(products, "create", new_vals = new_vals)
            self.env['product.template'].api_dw_product(products)
            
        return products
            
        
    def write(self, vals):
        res = super(ProductTemplateExt, self).write(vals)
        
        if self.write_date != self.create_date:
            # the result of the super() is a bool, so we need to search for the product template object to pass to the api function
            product = request.env['product.template'].search([('id', '=', self.id)], limit=1)
            
            test_import = self._context.get('test_import')
            copy_context = self._context.get('copy_context')
            # if we are not testing and duplicating
            if not test_import and not copy_context:
                self.env['product.template'].api_dw_product(product)
        return res
    
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

            new_log_id = activity_log_model.create(new_activity_log_vals)

            if method == 'create':
                new_log_id[0].create_log_on_create(new_vals[rec['id']], self._name)
            elif method == 'write':
                new_log_id[0].create_log_on_write(new_vals[rec['id']], old_vals[rec['id']],self._name)
                pass
            else:
                new_log_id[0].create_log_on_unlink(old_vals[rec['id']], self._name)

        return None
    
# PRODUCT =======================================================
class ProductExt(models.Model):
    _inherit = 'product.product'
    
    default_code = fields.Char('Internal Reference', index=True, required=True)
    
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.product'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + product_tmpl.default_code))