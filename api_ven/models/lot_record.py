from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
import datetime as dt
from datetime import datetime
import time
from odoo import http
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import base64
import urllib.request
import re
import hmac
import hashlib

"""
    Summary Brief:
    - This is lot records CUSTOM MODULE.
    - This is not DEFULT ODOO SERIAL/LOT NUMBER MODULE. But the behavior basic algorithm is same.
    - This models is creating because we need the lot records in ODOO JUST AS THE RECORDS

    LOGIC:
    1.   Odoo will request lot records data base on the product and the owner code.
    2.   WMS will send the lot records
    
    3.   Odoo will process the lot records data
    3.1. Odoo will validate the header that WMS send to Odoo
    3.2. Odoo will validate the line
    3.3. Odoo will checking with existing product and each the other

    4.   If lot records already existing, Odoo will re-write the data. If not, Odoo will create new lot records
"""

# Because we need the relation to with the warehouse. There for we need the relation between warehouse and the lot records
class StockWarehouseExt(models.Model):
    _inherit = "stock.warehouse"

    # Additional relation field
    lot_stock_id = fields.Many2one(
        'stock.location', 'Location Stock',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        required=True, check_company=True)

class ProductLotRecord(models.Model):
    _name = 'lot_record.lot_record'
    _description = 'WMS x Odoo Lot Record'
    _order = 'name, id'

    # lot records field
    name = fields.Char(
        'Lot Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True, help="Unique Lot Number", index=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    product_id = fields.Many2one(
        'product.product', 'Product', index=True, required=True, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_id.uom_id', store=True)
    quantity_on_hand = fields.Float('Quantity On Hand')
    available_quantity = fields.Float('Available Quantity')
    stock_status_code = fields.Selection([("NM", "Normal"),("DM", "Damage"),("ED","Expired"),("OBS","Obsolette"),("PR","Product Recall"),("RJCT","Reject"),],string="Stock Status Code", default='NM')
    expired_date = fields.Date('Expired Date')

    

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        
        '''
        - Checking the unique lot. It will pretend new lot name have same lot name with the previous lot
        - This is same logic as the serial/lot Odoo default funtion
        '''
        
        domain = [('product_id', 'in', self.product_id.ids),
                  ('company_id', 'in', self.company_id.ids),
                  ('name', 'in', self.mapped('name'))]
        fields = ['company_id', 'product_id', 'name']
        groupby = ['company_id', 'product_id', 'name']
        records = self.read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(rec['product_id'][0]).display_name
                error_message_lines.append(_(" - Product: %s, Serial Number: %s", product_name, rec['name']))
        if error_message_lines:
            raise ValidationError(_('The combination of serial number and product must be unique across a company.\nFollowing combination contains duplicates:\n') + '\n'.join(error_message_lines))

    @api.model_create_multi
    def create(self, vals_list):
        
        '''
        - This function has the same behavior for create function in Odoo lot/serial models
        - This function has a 2 job. First is calidate the unique name (validation) and then create the models
        '''
        
        self._check_unique_lot()
        return super(ProductLotRecord, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    
    def write(self, vals):
        '''
        This function has the same bahavior for write function in Odoo lot/serial models.
        '''

        # Pretend user to change company_id
        if 'company_id' in vals:
            for lot in self:
                if lot.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))

        # Pretend the user to change product ID
        if 'product_id' in vals and any(vals['product_id'] != lot.product_id.id for lot in self):
            move_lines = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('product_id', '!=', vals['product_id'])])
            if move_lines:
                raise UserError(_(
                    'You are not allowed to change the product linked to a serial or lot number '
                    'if some stock moves have already been created with that number. '
                    'This would lead to inconsistencies in your stock.'
                ))

        # Re-write the lot_records
        return super(ProductLotRecord, self).write(vals)

    def get_lot_list(self, product_id):
        '''
        This function was the API between Odoo and WMS where Odoo will request (Get) the list of lot in WMS based on 
        the owner code and product
        '''
        
        error = {}

        # The endpoint in wms (must change this to prd endpoint if we want to patch to prd)
        apiurl = "https://cloud1.boonsoftware.com/trn_avi_api/getlotlist"
        
        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"

        # Create the header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }

        # Preparate the request payload from Odoo to WMS
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "ownerCode": owner_code,
            "product": product_id
        }

        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'GET_LOT'
            })

            api_log['status'] = 'process'
        except Exception as e:
            error['Error'] = str(e)
            is_error = True

        # Create the incoming txt
        try:
            api_log['incoming_txt'] = request.env['ir.attachment'].create({
                'name': str(api_log['name']) + '_in.txt',
                'type': 'binary',
                'datas': base64.b64encode(bytes(str(payload), 'utf-8')),
                'res_model': 'api_ven.api_ven',
                'res_id': api_log['id'],
                'company_id': self.env.context['allowed_company_ids'][0],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True

        # Post the API request 
        resp = requests.get(apiurl, data=json.dumps(payload), headers=headers)

        # Update the response date and response message base on the API
        api_log['response_date'] = datetime.now()
        api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))

        # Changing the WMS response the list in python
        ret = json.loads(resp.text)

        # Create response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            # 'company_id': 1,
            'mimetype': 'text/plain'
        })

        if resp.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'


        return ret
        
    def lot_adjustment(self, product_sku):

        '''
        This function will process the lot list information that we get from get_lot_list API.
        '''

        error = {}
        is_error = False
        
        json_return = self.get_lot_list(product_sku)

        # (1) Header Validation ========================

        # (1.1) Header not null validation ========================

        # (1.1.1) Product not null validation
        if json_return['product'] == "":
            error["Error"] = "Field product is blank"
            is_error = True

        # (1.1.2) Product not null validation
        if json_return['ownerCode'] == "":
            error["Error"] = "Field owner code is blank"
            is_error = True
            
        # (1.1) Header not null validation [Done] ============================

        # (1.2) Header relation validation ============================

        # (1.2.1) Product Relation Validation
        try:
            existing_product = request.env['product.product'].search([('default_code', '=', json_return['product'])], limit=1)
        except Exception as e:
            error['Error'] = "Product not exist"
            is_error = True

        # (1.2) Header relation validation [Done] ============================

        # (1.3) Lot_list not empty validation
        
        lot_list = json_return.get('lotList')
        
        if not lot_list:
            error["Error"] = "There is no existing lot information for this product"
            is_error = True

        # (1.3) Lot list Validation [DONE] =============

        # (1) Header Validation [DONE] ============================

        # (2) Lot Adjustment Process =============
        
        try:
            for detail_lot in lot_list:
                is_newLot = False
                
                # (2.1) Checking not null validation
    
                # (2.1.1) Checking if the lotNo is null or not
                if detail_lot['lotNo'] == "":
                    error["Error"] = "Field lotNo is blank"
                    is_error = True
                    break
    
                # (2.1.2) Checking if the warehouseCode is null or not
                if detail_lot['warehouseCode'] == "":
                    error["Error"] = "Field warehouseCode is blank"
                    is_error = True
                    break

                # (2.1.3) Checking if the quantityOnHand is null or not
                if detail_lot['quantityOnHand'] == "":
                    error["Error"] = "Field quantityOnHand is blank"
                    is_error = True
                    break

                # (2.1.4) Checking if the availableQuantity is null or not
                if detail_lot['availableQuantity'] == "":
                    error["Error"] = "Field availableQuantity is blank"
                    is_error = True
                    break

                # (2.1.5) Checking if the availableQuantity is null or not
                if detail_lot['stockStatusCode'] == "":
                    error["stockStatusCode"] = "Field stockStatusCode is blank"
                    is_error = True
                    break
    
                # (2.1.6) Checking if the expiryDate is null or not
                if detail_lot['expiryDate'] == "":
                    error["Error"] = "Field expiryDate is blank"
                    is_error = True
                    break
    
                # (2.2) Checking the relationship of some field =========================
    
                # (2.2.1) Checking existant of lotNo
                # In here, we checking the lot first because the lot record not integrate into Purchase model yet.
                # So, it will be a case where WMS will send a new lot number into Odoo and we must capture it
                existing_lot = request.env['lot_record.lot_record'].search([('name', '=', detail_lot['lotNo'])])
                
                if not existing_lot:
                    is_newLot = True
                
                # (2.2) Checking the relationship of some field [DONE] =========================
    
                # (2.3) Lot_id Adjustment Process =========================

                rawStr_expiredDate = detail_lot['expiryDate']
                
                new_expiredDate = datetime.strptime(rawStr_expiredDate, '%d/%m/%Y')
                
                if is_newLot:
                    request.env['lot_record.lot_record'].create({
                        'name': detail_lot['lotNo'],
                        'company_id': self.env.context['allowed_company_ids'][0],
                        'product_id': existing_product['id'],
                        'quantity_on_hand': detail_lot['quantityOnHand'],
                        'available_quantity': detail_lot['availableQuantity'],
                        'stock_status_code': detail_lot['stockStatusCode'],
                        'expired_date': new_expiredDate
                    })
                else:
                    request.env['lot_record.lot_record'].write({
                        'name': detail_lot['lotNo'],
                        'company_id': self.env.context['allowed_company_ids'][0],
                        'product_id': existing_product['id'],
                        'quantity_on_hand': detail_lot['quantityOnHand'],
                        'available_quantity': detail_lot['availableQuantity'],
                        'stock_status_code': detail_lot['stockStatusCode'],
                        'expired_date': new_expiredDate
                    })
                    
        except Exception as e:
            error["Error"] = str(e)
            is_error = True
            
        if is_error:
            raise UserError (f"Error found with note: {error['Error']}. Please contact Boonsoftware Consultant!")


class SaleOrderLine(models.Model):
    '''
    This function will control about "Lot" Button in Sales Order.
    This function will get the Existing Product Internal Reference in Sale Order Line.
    '''
    _inherit = 'sale.order.line'
    
    def call_lot_adjustment(self):
        product_id = self.env.context.get('default_product_id')
        lot_record_model = self.env['lot_record.lot_record']
        product = self.env['product.product'].browse(product_id)
        product_code = product.default_code
        if product_code:
            lot_record_model.lot_adjustment(product_code)

        return True