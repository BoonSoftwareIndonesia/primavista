# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.line'
    _description = 'Product Move Line'
    # _auto = False

    id = fields.Integer(string="Id",readonly=True)
    pm = fields.Many2one('product_move.product_move', string="Product Move",readonly=True)
    io_code = fields.Char(string="IO Code",readonly=True)
    trans_code = fields.Char(string="Trans Code",readonly=True)
    product = fields.Many2one('product.product', string="Product",readonly=True)
    quantity = fields.Float(string="Quantity",readonly=True)
    
    
    
    