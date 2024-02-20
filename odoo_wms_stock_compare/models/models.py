from odoo import models, fields, api


class odoo_wms_stock_compare(models.Model):
    _name = 'odoo_wms_stock_compare.odoo_wms_stock_compare'
    _description = 'odoo_wms_stock_compare.odoo_wms_stock_compare'

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    product_id = fields.Many2one(
        'product.product', 'Product', index=True, required=True, check_company=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any).")
    
    odoo_quantity_on_hand = fields.Float(string='Odoo Quantity On Hand')
    wms_quantity_on_hand = fields.Float(string='WMS Quantity On Hand')
    odoo_wms_diff = fields.Float(string='Deficiency (Odoo - WMS)')

    @api.model_create_multi
    def create(self, vals_list):
        return super(odoo_wms_stock_compare, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    # This function has the same bahavior for write function in Odoo lot/serial models.
    def write(self, vals):
        # Re-write the lot_records
        return super(ProductLotRecord, self).write(vals)