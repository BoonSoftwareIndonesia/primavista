# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.product_move'
    _description = 'Product Move'

    id = fields.Integer()
    start_date = fields.Datetime(string="Start Date")
    product = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="Quantity")
    value = fields.Float(string="Value")
    
    

