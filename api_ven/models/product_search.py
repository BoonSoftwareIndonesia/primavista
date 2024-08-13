from odoo import models, fields, api
from odoo.http import request, Response

class product_categ (models.Model):
    _inherit = "purchase.order"

    # define field

    
    # x_product_category = fields.selection
    x_studio_product_category_3 = fields.Selection(
        selection='_get_product_categories',
        string='Product Category',
        store=True,
    )

    def _get_product_categories(self):        
        return [(category.display_name, category.display_name) for category in self.env['product.category'].search([])]

# salah 1 cara: override function search
# keyword: context, domain
