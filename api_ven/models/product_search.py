from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Field Selection untuk memilih kategori produk
    x_studio_product_category_3 = fields.Selection(
        selection='_get_product_categories',
        string='Product Category',
        store=True,
    )
    
    def _get_product_categories(self):
        # Mengambil semua kategori produk dari model product.category
        return [(category.id, category.display_name) for category in self.env['product.category'].search([])]

    @api.onchange('x_studio_product_category_3')
    def _onchange_product_category(self):
        # When the product category changes, apply the domain to product_id in the order lines
        if self.x_studio_product_category_3:
            category_id = int(self.x_studio_product_category_3)
            for line in self.order_line:
                line.product_id = False  # Clear current product selection
            return {
                'domain': {
                    'order_line.product_id': [('categ_id', '=', category_id)]
                }
            }
        else:
            return {'domain': {'order_line.product_id': []}}

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.order_id.x_studio_product_category_3:
            return {
                'domain': {
                    'product_id': [('categ_id', '=', int(self.order_id.x_studio_product_category_3))]
                }
            }
        else:
            return {'domain': {'product_id': []}}




     

# salah 1 cara: override function search
# keyword: context, domain
