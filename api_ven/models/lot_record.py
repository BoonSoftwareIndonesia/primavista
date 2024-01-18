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

class StockWarehouseExt(models.Model):
    _inherit = "stock.warehouse"

    lot_stock_id = fields.Many2one(
        'stock.location', 'Location Stock',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        required=True, check_company=True)

class ProductLotRecord(models.Model):
    _name = 'lot_record.lot_record'
    _description = 'WMS x Odoo Lot Record'
    _order = 'name, id'

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

    def _domain_product_id(self):
        domain = [
            "('tracking', '!=', 'none')",
            "('type', '=', 'product')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        return '[' + ', '.join(domain) + ']'

    @api.model_create_multi
    def create(self, vals_list):
        self._check_unique_lot()
        return super(ProductLotRecord, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def write(self, vals):
        if 'company_id' in vals:
            for lot in self:
                if lot.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'product_id' in vals and any(vals['product_id'] != lot.product_id.id for lot in self):
            move_lines = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('product_id', '!=', vals['product_id'])])
            if move_lines:
                raise UserError(_(
                    'You are not allowed to change the product linked to a serial or lot number '
                    'if some stock moves have already been created with that number. '
                    'This would lead to inconsistencies in your stock.'
                ))
        return super(ProductLotRecord, self).write(vals)

    def get_lot_list(self, product_id):
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

        # Test call method from sales order line
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

        api_log['response_date'] = datetime.now()
        api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))

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
        # raise UserError(f"{json_return}")
        
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
                # raise UserError(f"quantityOnHand: {detail_lot.get('quantityOnHand')}")
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
                # So, it will be a case where WMS will send new lot number into Odoo and we must capture it
                existing_lot = request.env['lot_record.lot_record'].search([('name', '=', detail_lot['lotNo'])])
                
                if not existing_lot:
                    is_newLot = True

                # raise UserError(f"{detail_lot['stockStatusCode']}")
                
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