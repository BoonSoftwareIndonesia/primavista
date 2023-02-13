# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ActivityLogLine(models.Model):
    _name = 'stock_compare.wms_stock_line'
    _description = 'WMS Stock Lines'

    id = fields.Integer()
    wms_stock_id = fields.Many2one('stock_compare.wms_stock')
    product = fields.Char('Product')
    odoo_quantity = fields.Float('Odoo Quantity')
    wms_quantity = fields.Float('WMS Quantity')
    lot_id = fields.Char('Lot Number')
    expiry_date = fields.Datetime('Expiry Date')
    warehouse = fields.Char('Warehouse')
    remarks = fields.Char('Remarks')
    diff_quantity = fields.Float('Qty Difference')
    
    