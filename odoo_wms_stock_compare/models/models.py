from odoo import models, fields, api


class odoo_wms_stock_compare(models.Model):
    _name = 'odoo_wms_stock_compare.odoo_wms_stock_compare'
    _description = 'odoo_wms_stock_compare.odoo_wms_stock_compare'

    def _compute_quantity_diff(self):
        self.odoo_wms_diff = self.odoo_quantity_on_hand - self.wms_quantity_on_hand

    # company_id = fields.Many2one('res.company', 'Company', required=True, index=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    product_id = fields.Many2one(
        'product.product', 'Product', index=True, required=True, check_company=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any).")
    
    odoo_quantity_on_hand = fields.Float(string='Odoo Quantity On Hand')
    wms_quantity_on_hand = fields.Float(string='WMS Quantity On Hand')
    odoo_wms_diff = fields.Float(string='Deficiency (Odoo - WMS)', readonly=True, compute='_compute_quantity_diff')