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