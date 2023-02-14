# -*- coding: utf-8 -*-

from odoo import models, fields, api

class WmsStockLine(models.Model):
    _name = 'stock_compare.wms_stock_line'
    _description = 'WMS Stock Lines'

    id = fields.Integer()
    wms_stock_id = fields.Many2one('stock_compare.wms_stock')
    product = fields.Char('Product')
    product_id = fields.Integer('Product ID', compute='_compute_product_id')
    odoo_quantity = fields.Float('Odoo Quantity')
    wms_quantity = fields.Float('WMS Quantity')
    lot_id = fields.Char('Lot Number')
    expiry_date = fields.Datetime('Expiry Date')
    warehouse = fields.Char('Warehouse')
    remarks = fields.Char('Remarks')
    diff_quantity = fields.Float('Qty Difference')
    
    # id = fields.Integer()
    # wms_stock_id = fields.Many2one('stock_compare.wms_stock')
    # product = fields.One2many('stock_compare.stock_report_line.product', string='Product')
    # wms_quantity = fields.Float('WMS Quantity')
    # lot_id = fields.Many2one('stock_compare.stock_report_line.lot_id', string='Lot Number')
    # expiry_date = fields.Many2one('stock_compare.stock_report_line.expiry_date', string='Expiry Date')
    # warehouse = fields.Many2one('stock_compare.stock_report_line.warehouse', string='Warehouse')
    
    
    @api.depends('product')
    def _compute_product_id(self):
        for rec in self:
            products = self.env['product.product'].search([('default_code','=',rec.product)])

            if products.id:
                rec.product_id = products.id
            else:
                rec.product_id = -1
                
    def _calculate_wms_stock(self):
        # WMS Stock Lines
        wms_stock_lines = self.env['stock_compare.wms_stock_line'].search([])

        for line in wms_stock_lines:
            stock_quants = self.env['stock.quant'].search([('product_id','=',line.product),('warehouse_id','=',line.warehouse), ('lot_id','=', line.lot_id)]).qty_available

            new_odoo_quantity = 0
            new_diff_quantity = line.wms_quantity * -1

            if stock_quants is not False:
                new_odoo_quantity = sum(stock_quants)
                new_diff_quantity = line.wms_quantity - new_odoo_quantity

            line.write({
                'odoo_quantity': new_odoo_quantity,
                'new_diff_quantity': new_diff_quantity
            })
            
            
    #     def update_odoo_qty(self):
    #         odoo_product = self.env['product.product'].search([('default_code','=',self.product)])
        
#         qty_available = 0
#         diff = self.wms_quantity * -1
        
#         if odoo_product:
#             for p in odoo_product:
#                 qty_available = p.qty_available
#                 diff = self.wms_quantity - p.qty_available
            
#         self.write({
#             "odoo_quantity": qty_available,
#             "diff_quantity": diff
#         })