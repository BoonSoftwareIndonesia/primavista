from odoo import models, fields, api
from odoo.http import request, Response
from odoo.exceptions import UserError
from datetime import datetime


# Override product template =============================
class ProductTemplateExt(models.Model):
    _inherit = 'product.template'
    
    # Override field(s)
    default_code = fields.Char(
        'Internal Reference', 
        compute='_compute_default_code',
        inverse='_set_default_code', 
        store=True, 
        required=True)
    
    # Constraint for default_code, ensure no duplicate default code =============================
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.template'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                # If there is a duplicate, raise user error
                if is_duplicate:
                    raise UserError(('Duplicate exists product.template: ' + product_tmpl.default_code))
                    
    # Copy context =============================
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if 'copy_context' not in self._context:
            # If copy context has not been set before
            res = super(ProductTemplateExt, self).with_context(copy_context=True).copy(default=default)
        else:
            # If copy context has been set before
            res = super(ProductTemplateExt, self).copy(default=default)
        return res
    
    
    # Override product template's create() =============================
    @api.model_create_multi
    def create(self, vals_list):
        # If copy_context is False (not duplicating) and test_import has not been set (not importing or testing import)
        if not self._context.get('copy_context') and 'test_import' not in self._context:
            # Get on_the_fly_context from product.product's create()
            otf_context = self._context.get('on_the_fly_context')
            
            # If otf_context has value, then we are creating a product on the fly
            if otf_context:
                # Get the product's default_code and standard_price
                otf_context = otf_context.split("-")
                vals_list[0]['default_code'] = otf_context[0]
                vals_list[0]['standard_price'] = otf_context[1]
            
            # If default_code is null, raise user error
            if vals_list[0]['default_code'] is False:
                raise UserError(('Internal reference cannot be null (product template-create)'))
            # If standard_price is null, raise user error
            if vals_list[0]['standard_price'] is False:
                raise UserError(('Cost cannot be null (product template-create)'))
        # raise UserError(str(vals_list))
        
        # Call the super() method
        products = super(ProductTemplateExt, self).create(vals_list)
        
        # Get the test_import context
        test_import = self._context.get('test_import')
        
        # If we are not testing an import, send API to WMS and create activity log
        if not test_import:
            # Get the new product's values
            new_vals = {}
            for rec in products:
                for vals, rec in zip(vals_list, products):
                    new_vals[rec.id] = vals
            
            # Create activity log
            self.create_activity_logs(products, "create", new_vals = new_vals)
            
            # Send API to WMS
            self.env['product.template'].api_dw_product(products)
            
        return products
            
        
    # Override product template's write() =============================
    def write(self, vals):
        # Get the old values before updating
        old_vals = {
                rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())
        }
        
        # Call the super() method
        res = super(ProductTemplateExt, self).write(vals)
        
        # If the product's write_date and create_date are different, we are doing an update, so we can proceed
        if self.write_date != self.create_date:
            # The result of the super() method is a bool, so we need to search for the product template object 
            # to pass to the api function
            product = request.env['product.template'].search([('id', '=', self.id)], limit=1)
            
            # Get test_import
            test_import = self._context.get('test_import')
            # Get copy_context
            copy_context = self._context.get('copy_context')
            
            # If we are not testing or duplicating, send api
            if not test_import and not copy_context:
                # Get the new values after product update
                new_vals = {rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())}
                # Create activity log for product update
                self.create_activity_logs(self, "write", new_vals=new_vals, old_vals=old_vals)
                # Send API to WMS 
                self.env['product.template'].api_dw_product(product)
        return res
    
    
    # Create activity log =============================
    def create_activity_logs(self, new_records, method, new_vals = {}, old_vals = {}):
        # Assign the activity_log model to a variable
        activity_log_model = self.env['api_ven.activity_log']
        # Get the current model's name (product.template)
        model_model = self.env[self._name]

        # Get the current user's id
        curr_user_id = self._context
        curr_user_id = curr_user_id.get('uid')
        # Get the current user's name
        curr_user_name = self.env['res.users'].browse(curr_user_id)

        # Declare the values for the activity log's fields
        for rec in new_records:
            new_activity_log_vals = {
                'method': method,
                'user':curr_user_id,
                'user_name':curr_user_name[0].name,
                'model_id': self._name,
                'resource_id': rec['id'],
                'resource_name': rec['name']
            }

            # Create activity log
            new_log_id = activity_log_model.create(new_activity_log_vals)

            if method == 'create':
                # If we are creating a new partner, call create_log_on_create()
                new_log_id[0].create_log_on_create(new_vals[rec['id']], self._name)
            elif method == 'write':
                # If we are updating an existing partner, call create_log_on_write()
                new_log_id[0].create_log_on_write(new_vals[rec['id']], old_vals[rec['id']],self._name)
                pass
            else:
                # If we are deleting an existing partner, call create_log_on_unlink()
                new_log_id[0].create_log_on_unlink(old_vals[rec['id']], self._name)

        return None
    
    
    # Override product deletion to create activity log =============================
    def unlink(self):
        old_vals = {}
        records = []
        
        for rec in self:
            # Get the values of the product that will be deleted
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
        
        # Call the super() method
        super(ProductTemplateExt, self).unlink()
        
        # Call create_activity_logs() to trigger the creation of an activity log for product deletion
        self.create_activity_logs(records, "unlink" , old_vals = old_vals)
        
        return None
  


    
# Override product =============================
class ProductExt(models.Model):
    _inherit = 'product.product'
    
    # Override field(s)
    default_code = fields.Char('Internal Reference', index=True, required=True)
    
    # Constraint for default_code, ensure no duplicate default_code =============================
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.product'].search([('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code)])
                # If a duplicate exists, raise user error
                if is_duplicate:
                    raise UserError(('Duplicate exists product.product: ' + product_tmpl.default_code))
    
    
    # Override product.product's create() =============================
    @api.model_create_multi
    def create(self, vals_list):
        # If in vals_list there is default_code, then it is a product create on the fly
        # raise UserError(f"{vals_list}")
        if 'default_code' in vals_list[0]:
            # If copy_context is False (not duplicating) and test_import has not been set (not testing import or importing)
            if not self._context.get('copy_context') and 'test_import' not in self._context:
                # Concatenate default code and standard price. This will be the value of the on_the_fly_context
                # This will be sent to product.template's create() 
                # And the value of the context will be used there to be sent to WMS
                context_content = str(vals_list[0]["default_code"]) + "-" + str(vals_list[0]["standard_price"])
                
                # Send default_code and standard_price info to product.template create for create on the fly 
                # by using on_the_fly_context 
                res = super(ProductExt, self.with_context(on_the_fly_context = context_content, create_product_product=True)).create(vals_list)
        
            return res
        # addon - v
        else:
            for vals in vals_list:
                self.product_tmpl_id._sanitize_vals(vals)
            products = super(ProductExt, self.with_context(create_product_product=True)).create(vals_list)
            # `_get_variant_id_for_combination` depends on existing variants
            self.clear_caches()
            return products