from odoo import models, fields, api
# from openerp.osv import osv
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
import datetime as dt
from datetime import datetime
from odoo import http
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import base64
import urllib.request
import re

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
        
    x_regular_discount = fields.Float(string='Discount (%)')

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'x_regular_discount')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.x_regular_discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_subtotal': taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
            })
                
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_discount = fields.Float(string='Discount Amount', compute='_compute_x_discount', store=True)

    @api.depends('purchase_line_id.x_regular_discount')
    def _compute_x_discount(self):
        for line in self:
            if line.purchase_line_id:
                line.x_discount = line.purchase_line_id.x_regular_discount
            else:
                line.x_discount = 0.0
    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def _compute_tax_totals_json(self):        
        super(PurchaseOrder, self)._compute_tax_totals_json()
        for order in self:
            if order.tax_totals_json:
                # Load the JSON string into a dictionary
                tax_totals_json_dict = json.loads(order.tax_totals_json)
                
                # Update tax_group_amount and formatted_tax_group_amount
                price_tax = order.amount_tax  # Assuming this is the correct field for price tax
                formatted_price_tax = "Rp\u00a0{:,.2f}".format(price_tax)
                
                # Update tax_group_base_amount and formatted_tax_group_base_amount
                amount_total = order.amount_total
                formatted_amount_total = "Rp\u00a0{:,.2f}".format(amount_total)
                
                for group in tax_totals_json_dict.get('groups_by_subtotal', {}).get('Untaxed Amount', []):
                    group['tax_group_amount'] = price_tax
                    group['formatted_tax_group_amount'] = formatted_price_tax
                    group['tax_group_base_amount'] = amount_total
                    group['formatted_tax_group_base_amount'] = formatted_amount_total
                
                # Convert the dictionary back to a JSON string
                formatted_json = json.dumps(tax_totals_json_dict, indent=4)
                
                # For debugging purposes: raise a UserError to display the modified JSON
                # raise UserError(formatted_json)
                
                # Write the updated JSON string back to the order
                order.write({'tax_totals_json': formatted_json})