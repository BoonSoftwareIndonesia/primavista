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

"""
Summary Brief:
- This discount field is a field that functions to apply discount PO feature. There are 3 type of discount in discount PO.
    
Logic:
Regular Discount => Regular discount is a discount obtained from the reduction between the price of the item 
                    and the discount price (the usual calculation of discounts in general)

Gradation Discount => Gradation discount is a discount which is the result of a discount on the price after regular 
                      discounts are made.

Additional Discount => Additional discounts are discounts that given as regular discounts based on the item price
"""


class PurchaseOrderLineDiscount(models.Model):
    _inherit = 'purchase.order.line'

    # Additional Field for Discount feature in PO
    x_regular_discount = fields.Float(string='Regular Discount (%)', digits='Discount', default=0.00)
    x_gradation_discount = fields.Float(string='Gradation Discount (%)', digits='Discount', default=0.00)
    x_additional_discount = fields.Float(string='Additional Discount (%)', digits='Discount', default=0.00)

    # Regular discount calculation.
    # This function will return the value of the regular discount (not the final price)
    def _regular_discount_count(self, price_unit, regular_discount):

        # Returns will be made using general discount calculations
        return price_unit*(regular_discount/100)

    # Calculation of discount gradations.
    # This function will return the value of the gradient discount (not the final price)
    def _gradation_discount_count(self, price_unit, regular_discount, gradation_discount):

        # Validation if the gradasi discount detected but regular discount not detected:
        if regular_discount == 0.00 and gradation_discount > 0.00:
            raise UserError(f"Please input the regular discount first before assigning gradasi discount!")

        # The curr_regular_discount field will call the regular discount function to get the regular discount price first
        curr_regular_discount = self._regular_discount_count(price_unit, regular_discount)

        # In the return process, a deduction will be made first to get the initial price (the price after deducting 
        # the regular discount) then the discount calculation process will be carried out as usual
        return (price_unit - curr_regular_discount)*(gradation_discount/100)

    def _additional_discount_count(self, price_unit, regular_discount, additional_discount):

        # Validation if the gradasi discount detected but regular discount not detected:
        if regular_discount == 0.00 and additional_discount > 0.00:
            raise UserError(f"Please input the regular discount first before assigning additional discount!")

        # Penambahan discount is same logic as regular discount. So, it will calculated base on regular discount
        return price_unit*(additional_discount/100)

    
    # Re-write _compute_amount Odoo Default Funtion
    # We must re-write this function because this function is a function that handle between taxes and PO.
    # Beside that, this function will be TRIGGERED EVERY TIME WE CREATE OR WRITE THE PO LINE
    
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())

            # ======================================================
            # raise UserError(line.x_regular_discount)

            # Validation that pretend user to input gradation discount and additional discount in the same line
            if line.x_gradation_discount > 0.00 and line.x_additional_discount > 0.00:
                raise UserError(f"Gradation Discount can't be use together with additional discount!")


            # ======================================================
        
            # 1. Get the current regular, gradiation, and additional discount value and then we multiple with product_qty
            regular_discount = self._regular_discount_count(line.price_unit, line.x_regular_discount) * line.product_qty
            gradation_discount = self._gradation_discount_count(line.price_unit, line.x_regular_discount, line.x_gradation_discount) * line.product_qty
            additional_discount = self._additional_discount_count(line.price_unit, line.x_regular_discount, line.x_additional_discount) * line.product_qty

            # ======================================================
            
            # 2. All the current discount will be calculation as curr_subtotal
            curr_subtotal = (line.price_unit*line.product_qty) - regular_discount - gradation_discount - additional_discount

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