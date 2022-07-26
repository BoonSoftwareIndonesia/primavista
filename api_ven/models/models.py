# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class api_ven(models.Model):
#     _name = 'api_ven.api_ven'
#     _description = 'api_ven.api_ven'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
