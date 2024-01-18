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
    
    x_regular_discount = fields.Float(string='Regular Discount (%)', digits='Discount', default=0.0)
    x_gradasi_discount = fields.Float(string='Gradasi Discount (%)', digits='Discount', default=0.0)
    x_penambahan_discount = fields.Float(string='Penambahan Discount (%)', digits='Discount', default=0.0)

    def _regular_discount_count(self, price_unit, regular_discount):
        return price_unit*(regular_discount/100)

    def _gradasi_discount_count(self, price_unit, regular_discount, gradasi_discount):
        
        curr_regular_discount = self._regular_discount_count(price_unit, regular_discount)

        return (price_unit - curr_regular_discount)*(gradasi_discount/100)
        
    def _regular_discount_count(self, price_unit, penambahan_discount):
        return price_unit*(penambahan_discount/100)

    def discount_count(self, vals):
        
        regular_discount = self._regular_discount_count(vals.price_unit, vals.x_regular_discount) * vals.product_qty
        gradasi_discount = self._gradasi_discount_count(vals.price_unit, vals.x_regular_discount, vals.x_gradasi_discount) * vals.product_qty
        penambahan_discount = self._regular_discount_count(vals.price_unit, vals.x_penambahan_discount) * vals.product_qty

        curr_subtotal = vals.price_subtotal - regular_discount - gradasi_discount - penambahan_discount

        # raise UserError(f"regular_discount: {regular_discount} | gradasi_discount: {gradasi_discount} | penambahan_discount: {penambahan_discount} | curr_subtotal: {curr_subtotal}")

        curr_sales_order_line = request.env['purchase.order.line'].search([('id', '=', vals.id)], limit=1)

        curr_sales_order_line.update({
            'price_subtotal': curr_subtotal,
        })

        # raise UserError(f"Scurr_sales_order_line: {curr_sales_order_line}")
        
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())

            # ==================================================

            regular_discount = self._regular_discount_count(line.price_unit, line.x_regular_discount) * line.product_qty
            gradasi_discount = self._gradasi_discount_count(line.price_unit, line.x_regular_discount, line.x_gradasi_discount) * line.product_qty
            penambahan_discount = self._regular_discount_count(line.price_unit, line.x_penambahan_discount) * line.product_qty

            curr_subtotal = (line.price_unit*line.product_qty) - regular_discount - gradasi_discount - penambahan_discount

            taxes['total_excluded'] = curr_subtotal
            taxes['total_included'] = curr_subtotal + line.price_tax
                        
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

            # ===================================================
            
    # def write(self, values):
    #     if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
    #         raise UserError(_("You cannot change the type of a purchase order line. Instead you should delete the current line and create a new line of the proper type."))

    #     if 'product_qty' in values:
    #         precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         for line in self:
    #             if (
    #                 line.order_id.state == "purchase"
    #                 and float_compare(line.product_qty, values["product_qty"], precision_digits=precision) != 0
    #             ):
    #                 line.order_id.message_post_with_view('purchase.track_po_line_template',
    #                                                      values={'line': line, 'product_qty': values['product_qty']},
    #                                                      subtype_id=self.env.ref('mail.mt_note').id)
                    
    #     temporary_total_discount = 0.0

    #     if 'x_regular_discount' in values:
    #         temporary_total_discount += self.price_unit*(values.get('x_regular_discount')/100)
    #     else:
    #         if self.x_regular_discount > 0:
    #             temporary_total_discount += self.price_unit*(self.x_regular_discount/100)

    #     if 'x_gradasi_discount' in values:
    #         if 'x_regular_discount' in values:
    #             temp_reg_disc = self.price_unit*(values.get('x_regular_discount')/100)
    #             temporary_total_discount += temp_reg_disc*(values.get('x_gradasi_discount')/100)
    #         else:
    #             if self.x_regular_discount is None:
    #                 raise UserError(f"[1 - self] - Regular Discount not Found. Please full the regular discount first!")
    #             elif values.get('x_regular_discount') is None:
    #                 raise UserError(f"[1 - Values] - Regular Discount not Found. Please full the regular discount first!")
                
    #             if self.x_regular_discount > 0.00:
    #                 temp_reg_disc = self.price_unit*(self.x_regular_discount/100)
    #                 temporary_total_discount += temp_reg_disc*(values.get('x_gradasi_discount')/100)
    #     else:
    #         if self.x_gradasi_discount > 0.00 and not None:
    #             if 'x_regular_discount' in values:
    #                 temp_reg_disc = self.price_unit*(values.get('x_regular_discount')/100)
    #                 temporary_total_discount += temp_reg_disc*(self.x_gradasi_discount/100)
    #             else:
    #                 if self.x_regular_discount is None:
    #                     raise UserError(f"[2 - self] Regular Discount not Found. Please full the regular discount first!")
                    
    #                 if self.x_regular_discount > 0.00:
    #                     temp_reg_disc = self.price_unit*(self.x_regular_discount/100)
    #                     temporary_total_discount += temp_reg_disc*(self.x_gradasi_discount/100)
    #                 elif self.x_regular_discount == 0.00:
    #                     raise UserError(f"[2 - self 0.00] Regular Discount not Found. Please full the regular discount first!")

    #     if 'x_penambahan_discount' in values:
    #         temporary_total_discount += self.price_unit*(values.get('x_penambahan_discount')/100)
    #     else:
    #         if self.x_penambahan_discount > 0.00 and not None:
    #             temporary_total_discount += self.price_unit*(self.x_penambahan_discount/100)

    #     # raise UserError(f"Final Price = {self.price_unit} - {temporary_total_discount} | {self.price_unit - temporary_total_discount}")

    #     curr_price_subTotal = self.price_unit - temporary_total_discount

    #     # raise UserError(f"Curr_price = {curr_price_subTotal}")
        
    #     # self.write({
    #     #     'price_subtotal': curr_price_subTotal,
    #     # })
        
    #     self.price_subtotal = self.price_unit - temporary_total_discount

    #     if 'qty_received' in values:
    #         for line in self:
    #             line._track_qty_received(values['qty_received'])
    #     return super(PurchaseOrderDiscount, self).write(values)