from odoo import models, fields, api

class ActivityLogLine(models.Model):
    _name = 'stock_compare.stock_report_line'
    _description = 'Stock Report Lines'

    id = fields.Integer()
    wms_stock_id = fields.Many2one('stock_compare.wms_stock')
    product = fields.Many2one('stock_compare.wms_stock_line.product', string='Product')
    odoo_quantity = fields.Float('Odoo Quantity')
    wms_quantity = fields.Float('WMS Quantity')
    lot_id = fields.Many2one('stock_compare.wms_stock_line.lot_id', string='Lot Number')
    expiry_date = fields.Many2one('stock_compare.wms_stock_line.expiry_date', string='Expiry Date')
    warehouse = fields.Many2one('stock_compare.wms_stock_line.warehouse', string='Warehouse')
    diff_quantity = fields.Float('Qty Difference')
    
    # def generate_stock_report_line(self):
    #     wms_stock_lines = self.env['stock_compare.wms_stock_lines'].search([])