# -*- coding: utf-8 -*-

from odoo import models, fields, api


class stock_compare(models.Model):
    _name = 'stock_compare.stock_compare'
    _description = 'stock_compare.stock_compare'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()
    

    # @api.depends('value')
    # def _value_pc(self):
    #     for record in self:
    #         record.value2 = float(record.value) / 100