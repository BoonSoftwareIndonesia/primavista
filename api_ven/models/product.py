from odoo import models, fields, api
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from lxml import etree

# Override product template =============================
class ProductTemplateExt(models.Model):
    _inherit = 'product.template'        

    # Adding new field(s)
    x_product_brand = fields.Selection([("NA", "NA"),("Tom Ford", "Tom Ford"), ("3M", "3M"), ("AKMU", "AKMU"), ("ALPHA", "ALPHA"), ("APA", "APA"), ("BERNOFARM OTC", "BERNOFARM OTC"), ("DKT", "DKT"), ("ESSILOR NVG CONS", "ESSILOR NVG CONS"), ("GALENIUM PSC", "GALENIUM PSC"), ("GEO MEDICAL", "GEO MEDICAL"), ("JENNY HOUSE", "JENNY HOUSE"), ("KLARENS", "KLARENS"), ("MPS", "MPS"), ("ONEMED", "ONEMED"), ("SENSI", "SENSI"), ("TAKEDA OTC", "TAKEDA OTC"), ("THERASKIN", "THERASKIN"), ("VITAHEALTH CONS", "VITAHEALTH CONS"), ("NVG ESSILOR", "NVG ESSILOR"), ("ACUVUE", "ACUVUE"), ("BAUSCH LOMB IND", "BAUSCH LOMB IND"), ("ESSILOR 2.5 NVG", "ESSILOR 2.5 NVG"), ("FRESH EYE", "FRESH EYE"), ("HOSLIFE CARE", "HOSLIFE CARE"), ("JJMI", "JJMI"), ("KGM", "KGM"), ("KINO", "KINO"), ("KINO MEDICAL", "KINO MEDICAL"), ("MEIJI IND ETC", "MEIJI IND ETC"), ("OMRON", "OMRON"), ("OMRON CONS", "OMRON CONS"), ("OSS BLI", "OSS BLI"), ("OSS OTHER", "OSS OTHER"), ("VITAHEALTH", "VITAHEALTH")],string="Product Brand", default='NA')
    x_product_height = fields.Float(string="Product Height")
    x_product_length = fields.Float(string="Product Length")
    x_product_width = fields.Float(string="Product Width")
    x_is_lot_tracking = fields.Boolean(string="Tracking by Lot")

    # The custom field below is to add owner to products, PO, SO, DO, receipt, stock move, and res.partner. Make sure to change all fields on other models too if there's a change!
    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")
    ], string='Owner')    

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
                is_duplicate = request.env['product.template'].search([
                    ('id','!=',product_tmpl.id),
                    ('default_code', '=', product_tmpl.default_code), 
                    ('company_id', '=', self.env.context['allowed_company_ids'][0])
                ])
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
            vals_list[0]['default_code'] = vals_list[0]['default_code'].upper()

            
            # If standard_price is null, raise user error
            if vals_list[0]['standard_price'] is False:
                raise UserError(('Cost cannot be null (product template-create)'))

            vals_list[0]['company_id'] = self.env.context['allowed_company_ids'][0]
                        
        # Call the super() method
        products = super(ProductTemplateExt, self).create(vals_list)
        
        if products.categ_id:                        
            # Checking if user access the parent category or not            
            if not products.categ_id.parent_id:
                raise UserError(f"Can't create product because user using parent category! Please use the child category instead of parent category or contact your consultant!")
        
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

        # Set owner_name in product.product based on owner_name in product.template
        product_variants = self.env['product.product']
        for product_template, vals in zip(products, vals_list):
            owner_name = vals.get('owner_name')
            if owner_name:
                product_variants |= product_template.product_variant_id
        product_variants.write({'owner_name': owner_name})     
            
        return products
            
        
    # Override product template's write() =============================
    def write(self, vals):
        # Get the old values before updating
        old_vals = {
                rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())
        }
        
        # Call the super() method
        res = super(ProductTemplateExt, self).write(vals)

        if self.categ_id:               
            # Checking if user access the parent category or not
            if not self.categ_id.parent_id:
                # raise UserError(f"parent: {self.categ_id.parent_id.name} || Child: {self.categ_id.name}")
                raise UserError(f"Can't edit product because user using parent category! Please use the child category instead of parent category or contact your consultant!")
        
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

    # Adding additional field
    lot_record_id = fields.One2many('lot_record.lot_record', 'product_id',
        string = 'Lot Record ID')
    
    # Constraint for default_code, ensure no duplicate default_code =============================
    @api.constrains('default_code')
    def _check_default_code(self):
        for product_tmpl in self:
            if product_tmpl.default_code:
                is_duplicate = False
                is_duplicate = request.env['product.product'].search([
                    ('id','!=',product_tmpl.id),('default_code', '=', product_tmpl.default_code), ('company_id', '=', self.env.context['allowed_company_ids'][0])])
                # If a duplicate exists, raise user error
                if is_duplicate:
                    raise UserError(('Duplicate exists product.product: ' + product_tmpl.default_code))
    
    
    # Override product.product's create() =============================
    @api.model_create_multi
    def create(self, vals_list):
        # If in vals_list there is default_code, then it is a product create on the fly
        if 'default_code' in vals_list[0]:

            vals_list[0]['default_code'] = vals_list[0]['default_code'].upper()
            
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

# # # # # # # # # # # # # # # # # 
# CODE FOR EXCHANGE BEGINS HERE #
# # # # # # # # # # # # # # # # #            
            
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner')
    
    x_product_category_selection = fields.Selection(
        selection='_get_product_categories',
        string='Product Category',
        store=True, # This ensures the field's value is stored in the database        
    )

    def _get_product_categories(self):
        # This method returns the list of tuples for the selection field
        return [(category.display_name, category.display_name) for category in self.env['product.category'].search([])]

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            for picking in order.picking_ids:
                picking.x_doc_trans_code = order.x_studio_doc_trans_code

        for order in self:
            for picking in order.picking_ids:
                picking.write({'owner_name': order.owner_name})

        return res
                
    
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    x_total_quantity_receipt = fields.Float(string='Total Quantity', compute='_compute_total_quantity', store=True)

    @api.depends('move_lines.quantity_done')
    def _compute_total_quantity(self):
        for picking in self:
            picking.x_total_quantity_receipt = sum(picking.move_lines.mapped('quantity_done'))    
    
    # Custom field to store product categories
    x_product_category_selection = fields.Selection(
        selection='_get_product_categories',
        string='Product Category',
        store=True, # This ensures the field's value is stored in the database        
    )

    # Function to get all product categories
    def _get_product_categories(self):        
        return [(category.display_name, category.display_name) for category in self.env['product.category'].search([])]

    # Custom field to store doc trabs code
    x_doc_trans_code = fields.Selection(
        selection='_get_x_studio_doc_trans_codes',
        string='Doc Trans Code',
        store=True,
    )

    # custom field to store owner
    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner')
    
    @api.model
    def _get_x_studio_doc_trans_codes(self):
        # Fetch the field definition of x_studio_doc_trans_code from sale.order
        field = self.env['sale.order']._fields.get('x_studio_doc_trans_code')
        # Return the selection options
        return field.selection

    x_exo_number = fields.Char(string='EXO Number')

    @api.model
    def create(self, vals):        
        if vals.get('x_exo_number'):            
            # Check if the 'x_exo_number' is unique among non-cancelled pickings
            if self.search_count([('x_exo_number', '=', vals['x_exo_number']), ('state', '!=', 'cancel')]) > 0:
                raise ValidationError("Running Number has already been used!")
    
            # Check if the 'x_exo_number' matches any records
            matching_picking = self.env['stock.picking'].search([
                ('name', 'like', '%OUT%'),  # Search for names containing "OUT"
                ('x_doc_trans_code', '=', 'EXO'),
                ('name', '=', vals['x_exo_number'])
            ])
            if not matching_picking:
                raise ValidationError("The EXO Number must match the Running Number of any records!")
            
            # Check if the product category selection matches the delivery order
            if matching_picking and vals.get('x_product_category_selection'):
                delivery_order = matching_picking.filtered(lambda picking: picking.state == 'done')
                if not delivery_order:
                    raise ValidationError("No completed delivery order found for the matching EXO Number.")
                if vals['x_product_category_selection'] != delivery_order.x_product_category_selection:
                    raise ValidationError(f"The product category selection '{vals['x_product_category_selection']}' does not match the expected product category '{delivery_order.x_product_category_selection}' from the delivery order.")
                    
        return super(StockPicking, self).create(vals)
        
    # Validate quantity
    def button_validate(self):
        # Call super to perform default validation
        res = super(StockPicking, self).button_validate()

        # Call function to change owner_name in stock.quant
        for picking in self:            
            picking._update_quant_owner_name()
        return res
        
        # Iterate through each receipt
        for receipt in self.filtered(lambda r: r.picking_type_code == 'incoming' and r.x_doc_trans_code in ['EXI', 'EXO']):
            # Find related delivery order with the same 'x_exo_number'
            delivery_order = self.env['stock.picking'].search([
                ('picking_type_code', '=', 'outgoing'),
                ('x_doc_trans_code', '=', 'EXO'),                
                ('name', '=', receipt.x_exo_number)
            ], limit=1)

            # If no related delivery order found, raise validation error
            if not delivery_order:
                raise ValidationError(f"No related delivery order found for receipt {receipt.name}.")

            # Compare 'x_total_quantity' fields
            if receipt.x_total_quantity_receipt != delivery_order.x_total_quantity_receipt:
                raise ValidationError(f"Total quantity in receipt {receipt.name} ({receipt.x_total_quantity_receipt}) does not match with delivery order {delivery_order.name} ({delivery_order.x_total_quantity_receipt}).")

        return res

    def _update_quant_owner_name(self):
        for move in self.move_lines:
            for quant in move.product_id.stock_quant_ids:
                quant.owner_name = move.owner_name
        
class ProductTemplate(models.Model):
    _inherit = 'product.product'

    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner Name')
    
    # The two functions below allow us to modify the product selection popup so that it filters the product by the selected product category selection
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=None):
        if args is None:
            args = []

        # raise UserError(self.env.context.get('product_category_selection'))                
        # The context is defined using Odoo Studio. Please use self.env.context.get otherwise it would give out errors!     
        category_id = self.env.context.get('product_category_selection')
        if category_id:
            args.append(('categ_id', '=', category_id))

        owner_name = self.env.context.get('owner_name')
        if owner_name:
            args.append(('owner_name', '=', owner_name))        

        return super(ProductTemplate, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=False):
        if args is None:
            args = []

        # raise UserError(self.env.context.get('product_category_selection'))        
        category_id = self.env.context.get('product_category_selection')
        if category_id:
            args.append(('categ_id', '=', category_id))

        owner_name = self.env.context.get('owner_name')
        if owner_name:
            args.append(('owner_name', '=', owner_name))        

        return super(ProductTemplate, self).search(args, offset=offset, limit=limit, order=order, count=count)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner Name')

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner')    

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.picking_ids:
                # Assuming each purchase order has only one picking associated
                picking = order.picking_ids[0]
                picking.write({'owner_name': order.owner_name})
        return res

    def action_confirm(self):
        res = super(PurchaseOrder, self).action_confirm()
        
        for order in self:
            for picking in order.picking_ids:
                picking.write({'owner_name': order.owner_name})
        
        return res

    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()

        for order in self:
            for invoice in order.invoice_ids:
                invoice.write({
                    'amount_total': order.amount_total,
                    'amount_tax': order.amount_tax,
                    'amount_untaxed': order.amount_untaxed,
                    'tax_totals_json': order.tax_totals_json,
                    # Write other necessary fields here
                })

        return res        
                        
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_stock_moves(self, picking):
        """
        Prepare the stock moves based on the purchase order lines.
        Include the owner_name from the purchase.order.
        """
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        
        # Access the owner_name from the purchase.order
        owner_name = self.order_id.owner_name        
        
        # Include the owner_name in the stock moves
        for move in res:
            move['owner_name'] = owner_name
            
        return res
        
class StockMove(models.Model):
    _inherit = 'stock.move'

    owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")        
    ], string='Owner')