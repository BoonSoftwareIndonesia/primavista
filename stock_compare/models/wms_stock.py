# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ActivityLog(models.Model):
    _name = 'stock_compare.wms_stock'
    _description = 'WMS Stock'

    id = fields.Integer()
    wms_stock_line_ids = fields.One2many('stock_compare.wms_stock_line', 'wms_stock_id', string="Stock Lines")
    
    