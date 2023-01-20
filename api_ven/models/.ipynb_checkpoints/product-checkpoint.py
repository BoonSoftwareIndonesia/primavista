from odoo import models, fields, api
from odoo.http import request, Response
from odoo.exceptions import UserError
from datetime import datetime

class ProductTemplateExt(models.Model):
    _inherit = 'product.template'
    
    # override field(s)
    default_code = fields.Char(
        'Internal Reference', 
        compute='_compute_default_code',
        inverse='_set_default_code', 
        store=True, 
        required=True)
    
    # constraint for default_code
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.template'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + product_tmpl.default_code))
                    
    # copy context
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if 'copy_context' not in self._context:
            res = super(ProductTemplateExt, self).with_context(copy_context=True).copy(default=default)
        else:
            res = super(ProductTemplateExt, self).copy(default=default)
        return res
    
    # create
    @api.model_create_multi
    def create(self, vals_list):
        # if not self._context.get('copy_context') and 'test_import' not in self._context:
        #     otf_context = self._context.get('on_the_fly_context')
        #     if otf_context:
        #         otf_context = otf_context.split("-")
        #         vals_list[0]['default_code'] = otf_context[0]
        #         vals_list[0]['standard_price'] = otf_context[1]
        #     if vals_list[0]['default_code'] is False:
        #         raise UserError(('Internal reference cannot be null (product template-create)'))
        #     # raise UserError(str(vals_list[0]['default_code']))
        #     if vals_list[0]['standard_price'] is False:
        #         raise UserError(('Cost cannot be null (product template-create)'))
        # raise UserError(str(vals_list))
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
            
        
    # write
    def write(self, vals):
        # get the old vals
        old_vals = {
                rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())
        }
        
        res = super(ProductTemplateExt, self).write(vals)
        
        if self.write_date != self.create_date:
            # the result of the super() is a bool, so we need to search for the product template object to pass to the api function
            product = request.env['product.template'].search([('id', '=', self.id)], limit=1)
            
            test_import = self._context.get('test_import')
            copy_context = self._context.get('copy_context')
            
            # if we are not testing and duplicating, send api
            if not test_import and not copy_context:
                # get new vals
                new_vals = {rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())}
                # create activity log for partner update
                self.create_activity_logs(self, "write", new_vals=new_vals, old_vals=old_vals)
                # send api 
                self.env['product.template'].api_dw_product(product)
        return res
    
    def create_activity_logs(self, new_records, method, new_vals = {}, old_vals = {}):
        activity_log_model = self.env['api_ven.activity_log']
        model_model = self.env[self._name]

        curr_user_id = self._context
        curr_user_id = curr_user_id.get('uid')
        curr_user_name = self.env['res.users'].browse(curr_user_id)

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
    
    def unlink(self):
        old_vals = {}
        records = []
        
        for rec in self:
            # get old vals
            old_vals[rec.id] = {
                'default_code': "" if not rec.default_code else rec.default_code, 
                'name': "" if not rec.name else rec.name, 
                'uom_id': "" if not rec.uom_id.name else rec.uom_id.name,
                # 'whole_uom': "" if not rec.uom_id.name else rec.uom_id.name,
                # 'whole_denomination': "" if not rec.uom_id.ratio else rec.uom_id.ratio,
                'tracking': "" if not rec.tracking else rec.tracking, 
                'standard_price': "" if not rec.standard_price else rec.standard_price, 
            }
            records.append({'id': rec.id, 'name': rec.name})
        
        super(ProductTemplateExt, self).unlink()
        
        # create activity log for partner deletion
        self.create_activity_logs(records, "unlink" , old_vals = old_vals)
        
        return None
    
    
# PRODUCT =======================================================
class ProductExt(models.Model):
    _inherit = 'product.product'
    
    # override field(s)
    default_code = fields.Char('Internal Reference', index=True, required=True)
    
    # default code constraint
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.product'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                if is_duplicate:
                    raise UserError(('Duplicate exists: ' + product_tmpl.default_code))
    
#     @api.model_create_multi
#     def create(self, vals_list):
#         if not self._context.get('copy_context') and 'test_import' not in self._context:
#         # Send default_code and standard_price info to product.template create for on the fly product
#             context_content = str(vals_list[0]["default_code"]) + "-" + str(vals_list[0]["standard_price"])
#             res = super(ProductExt, self.with_context(on_the_fly_context = context_content, create_product_product=True)).create(vals_list)
        
#             return res