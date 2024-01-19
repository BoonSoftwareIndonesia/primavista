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

class PurchaseOrderLineDiscount(models.Model):
    _inherit = 'purchase.order.line'

    # Additional Field for Discount feature in PO
    x_regular_discount = fields.Float(string='Regular Discount (%)', digits='Discount', default=0.0)
    x_gradasi_discount = fields.Float(string='Gradasi Discount (%)', digits='Discount', default=0.0)
    x_penambahan_discount = fields.Float(string='Penambahan Discount (%)', digits='Discount', default=0.0)

    """
    Summary Brief:
    - This discount field is a field that functions only as a record in Odoo. (Before implementing PO integration between SAP and Odoo)
    
    Logic:
    Regular Discount => Regular discount is a discount obtained from the reduction between the price of the item 
                        and the discount price (the usual calculation of discounts in general)

    Gradasi Discount => Gradation discount is a discount which is the result of a discount on the price after regular 
                        discounts are made.

    Penambahan Discount => Penambahan discounts are discounts that given as additional discounts based on the item price
    """

    # Regular discount calculation.
    # This function will return the value of the regular discount (not the final price)
    def _regular_discount_count(self, price_unit, regular_discount):

        # Returns will be made using general discount calculations
        return price_unit*(regular_discount/100)

    # Calculation of discount gradations.
    # This function will return the value of the gradient discount (not the final price)
    def _gradasi_discount_count(self, price_unit, regular_discount, gradasi_discount):

        # The curr_regular_discount field will call the regular discount function to get the regular discount price first
        curr_regular_discount = self._regular_discount_count(price_unit, regular_discount)

        # In the return process, a deduction will be made first to get the initial price (the price after deducting 
        # the regular discount) then the discount calculation process will be carried out as usual
        return (price_unit - curr_regular_discount)*(gradasi_discount/100)

    
    # Re-write _compute_amount Odoo Default Funtion
    # We must re-write this function because this function is a function that handle between taxes and PO.
    # Beside that, this function will be TRIGGERED EVERY TIME WE CREATE OR WRITE THE PO LINE
    
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())

            # ======================================================
        
            # 1. Get the current regular, gradiation, and additional discount value and then we multiple with product_qty

            regular_discount = self._regular_discount_count(line.price_unit, line.x_regular_discount) * line.product_qty
            gradasi_discount = self._gradasi_discount_count(line.price_unit, line.x_regular_discount, line.x_gradasi_discount) * line.product_qty
            penambahan_discount = self._penambahan_discount_count(line.price_unit, line.x_penambahan_discount) * line.product_qty

            # ======================================================
            
            # 2. All the current discount will be calculation as curr_subtotal
            curr_subtotal = (line.price_unit*line.product_qty) - regular_discount - gradasi_discount - penambahan_discount

            # ======================================================
        
            # Since amount field will be handle by default field. So, we will use the default field where
            # taxes['total_excluded'] => amount that include discount value
            # taxes['total_included'] => amount that inlude discount value and tax value

            # 3. Re-calculating the taxes['total_excluded'] and taxes['total_include']  
            taxes['total_excluded'] = curr_subtotal
            taxes['total_included'] = curr_subtotal + line.price_tax

            # ======================================================

            # 4. Update the amount price that include price_tax, price_total, and pricec_subtotal
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

            # ======================================================