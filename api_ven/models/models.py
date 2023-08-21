# -*- coding: utf-8 -*-

from odoo import models, fields, api
from openerp.osv import osv
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


# Override for PO and SO return ======================
# Override stock move creation process when a PO is confirmed. 
# This prepares the stock moves data for one order line and returns a list of dictionary ready to be used in stock.move's create()
# So we can set the stock move's x_studio_opt_char_1 value with the value from the corresponding PO line's x_studio_opt_char_1
class PurchaseOrderLineExt(models.Model):
    _inherit = 'purchase.order.line'
    x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')

    # @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLineExt, self)._prepare_stock_moves(picking)
        for rec in res:
            rec['x_studio_opt_char_1'] = self.x_studio_opt_char_1
        return res

# Override stock move creation process when a SO is confirmed. 
# This prepares the stock moves data for one order line and returns a list of dictionary ready to be used in stock.move's create()
# So we can set the stock move's x_studio_opt_char_1 value with the value from the corresponding SO line's x_studio_line_no
class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'
    x_studio_line_no = fields.Char('x_studio_line_no')
    
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLineExt, self)._prepare_procurement_values(group_id)
        res.update({'x_studio_opt_char_1': self.x_studio_line_no})
        return res
    
    
# Override for importing customer and product ======================
class ImportInheritExt(models.TransientModel):
    _inherit = 'base_import.import'

    # For when importing new product or customer
    def execute_import(self, fields, columns, options, dryrun=False):
        # If user clicks import, set the dryrun and test_import context to True so we always test first before importing
        # This is to prevent odoo from sending an api log to wms when the user clicks import and there is an error in the file
        if dryrun == False:
            res = super(ImportInheritExt, self).with_context(test_import=True).execute_import(fields, columns, options, True)
            # If the messages is not [], there is an error, so just return
            # If the message is [], there is no error, so proceed 
            if str(res['messages']) != '[]':
                   return res
        
        if 'test_import' not in self._context:
            # If the context haven't been set, set the context
            res = super(ImportInheritExt, self).with_context(test_import=dryrun).execute_import(fields, columns, options, dryrun)
        else:
            # Else, no need to set the context
            res = super(ImportInheritExt, self).execute_import(fields, columns, options, dryrun)
        return res

    
    
class UomExt(models.Model):
    _inherit = 'uom.uom'
    ratio = fields.Float('Combined Ratio', compute='_compute_ratio', inverse='_set_ratio', store=False, required=True)

    
    
# API VEN MODEL ==========================================================================
class api_ven(models.Model):
    _name = 'api_ven.api_ven'
    _description = 'api_ven.api_ven'
    
    # The fields in the api_ven table
    name = fields.Char(string="Message ID", required=True, copy=False, readonly=True, index=True, default=lambda self: ('New'))
    incoming_msg = fields.Text(string="Incoming Message")
    response_msg = fields.Text(string="Response Message")
    status = fields.Selection([('new','New'),('process','Processing'),('success','Success'),('error','Error')])
    created_date = fields.Datetime(string="Created Date")
    response_date = fields.Datetime(string="Response Date")
    message_type = fields.Selection([('RCPT','CRT_RCPT'), ('DO','CRT_DO'), ('PO','DW_PO'), ('SO','DW_SO'), ('PO_RET','DW_PO_RET'), ('SO_RET','DW_SO_RET'), ('RCPT_RET','CRT_RCPT_RET'), ('DO_RET','CRT_DO_RET'), ('CUST','DW_CUST'), ('PROD','DW_PROD'), ('STOCK','STOCK_COMPARE'), ('ADJUST', 'STOCK_ADJUSTMENT'), ('FTKPD', 'FETCH_TOKOPEDIA')])
    incoming_txt = fields.Many2one('ir.attachment', string="Incoming txt", readonly=True)
    response_txt = fields.Many2one('ir.attachment', string="Response txt", readonly=True)
    raw_data = fields.Binary(string="Raw Data", attachment=True)
    raw_dataname = fields.Char(string="File Name")
    
    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == ('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('api.seq') or ('New')
        result = super(api_ven, self).create(vals)
        return result
    
    # @api.model
    # def testing(self):
    #     print('test');

    

# PURCHASE ORDER (DW_PO API) (Odoo to WMS) ==========================================================================
class ApiController(models.Model):
    _inherit = ['purchase.order']
    
    def api_dw_po(self, record):
            
        # The endpoint in wms (must change this to prd endpoint if we want to patch to prd)
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createasn"
        
        # A variable to store the value of the current line number
        line_no = 1
        # An array to store the PO lines
        po_lines = []
        # To store the origin of this PO (the SO(s) that generated this PO)
        res = ""
        unique_res = ""
        
        # To get the SO No that generated this PO
        # If this PO is generated from another SO, we also need to send the list of SO that generated this PO
        # Use regex to get the SO no only
        # Example: OP/00272 - SO/POV/2022/11/24/00178 -> SO/POV/2022/11/24/00178
        # re.findall() is used to return all non-overlapping matches of pattern in string, as a list of strings
        # The string is scanned left-to-right, and matches are returned in the order found.
        if record['origin']:
            res = re.findall(r'S[\w\/]*', record['origin'])
            unique_res = str(set(res))
        
        # Loop through all purchase order lines
        for line in record['order_line']:
            # If there is a PO line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue
            
            # Set the current line's x_studio_line_opt_char_1 as the value of the current line_no
            line['x_studio_opt_char_1'] = str(line_no)
            
            # Create po line (Refer to the mapping documentation)
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrdered": str(line['product_qty']),
#                 "uomCode": line['product_uom']['name'],
                "uomCode": "PCS",
                "stockStatusCode": "NM" if line['x_stock_status_code']  == False else line['x_stock_status_code'] 
            }
            # Increment the line_no
            line_no += 1
            # Append the current po_line to the po_lines array
            po_lines.append(po_line)
        
        # Catch the DO field
        # stock_picking_name = self.stock_picking.name
        
        # Create payload (Refer to the mapping documentation). These are the data that will be sent from Odoo to WMS
        # The access token for the WMS needs to be changed to prd's access token if we want to patch to prd
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {
                    "ownerReferences": "",
                    "poNo": "" if record['name'] == False else record['name'],
                    "supplierReferences": "" if record['partner_ref'] == False else record['partner_ref'],
                    "sender": "",
                    "documentTransCode":"" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
                    "ownerCode": "PRIMAVISTA",
#                     "warehouseCode": "" if record['picking_type_id']['warehouse_id']['code'] == False else record['picking_type_id']['warehouse_id']['code'],
                    "warehouseCode": "AVI",
                    "poDate": "" if record['date_approve'] == False else datetime.strftime(record['date_approve'], '%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['date_planned'] == False else datetime.strftime(record['date_planned'], '%d/%m/%Y'),
                    "otherReferences": "",
                    "remark1": "" if unique_res == False else unique_res,
                    "doNo": "",
                    "asnLine": po_lines
                }
            ]
        }
        
        # The header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'PO'
            })

            api_log['status'] = 'process'
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
        
        # Create incoming txt
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
        
        # Post API request
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)

        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        """if is_error == False:
            api_log['status'] = 'success'
        elif '"returnStatus":"-1"' in api_log['response_msg']:
            api_log['status'] = 'error'
        else:
            api_log['status'] = 'success'"""
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })

        
        
# SALES ORDER (DW_SO API) (Odoo to WMS) ==========================================================================        
class ApiControllerSO(models.Model):
    _inherit = "sale.order"
    
    def api_dw_so(self, record):
        # The endpoint in wms (must change this to prd endpoint if we want to patch to prd)
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createso"
        
        # A variable to store the value of the current line number
        line_no = 1
        # A variable to store the SO lines
        so_lines = []
        
        # Loop through all sale order lines
        for line in record['order_line']:
            # If there is a PO line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue
            
            # Set the current line's x_studio_line_no as the value of the current line_no
            line['x_studio_line_no'] = str(line_no)
            
            # Create so line (Refer to the mapping documentation)
            so_line = {
                "soLineOptChar1": line['x_studio_line_no'],
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrder": str(int(line['product_uom_qty'])),
#                 "originalOrderUOM": line['product_uom']['name'],
                "originalOrderUOM": "PCS",
                "lotNo": "LOT", 
                "filterTransactionCode": "NM" if line['x_stock_status_code']  == False else line['x_stock_status_code'],
                "soLineOptChar2": ""
            }
            
            # Increment the line_no
            line_no += 1
            # Append the current so_line to the so_lines array
            so_lines.append(so_line)
        
        # Create payload (Refer to the mapping documentation). These are the data that will be sent from Odoo to WMS
        # The access token for the WMS needs to be changed to prd's access token if we want to patch to prd
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
            "namespace": "http://www.boonsoftware.com/createSO/POV",
            "order":[
                {
                    "customerPO":"",
                    "reference":"" if record['name'] == False else record['name'],
                    "customerCode":"" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
                    "soHeaderOptChar3":"",
                    "documentTransCode":"" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
                    "orderDate":"" if record['date_order'] == False else datetime.strftime(record['date_order'], '%d/%m/%Y'),
                    "requestedDeliveryDate":"",
#                     "ownerCode":"" if record['x_studio_owner_code'] == False else record['x_studio_owner_code'],
                     "ownerCode":"PRIMAVISTA",
#                     "warehouseCode": "" if record['warehouse_id']['code'] == False else record['warehouse_id']['code'],
                    "warehouseCode": "AVI",
#                     "shipNo": "" if record['x_studio_internal_id'] == False else record['x_studio_internal_id'],
#                     "shipNo": "" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
#                     "shipNo": "" if record['partner_shipping_id']['name'] == False else record['partner_shipping_id']['name'],
                    "shipNo": "" if record['partner_shipping_id']['x_studio_customer_id'] == False else record['partner_shipping_id']['x_studio_customer_id'],
                    "shipAddress1":"" if record['partner_shipping_id']["street"] == False else record['partner_shipping_id']["street"],
                    "shipCity":"" if record['partner_shipping_id']["city"] == False else record['partner_shipping_id']["city"],
#                     "shipZipCode":"" if record['partner_shipping_id']["zip"] == False else record['partner_shipping_id']["zip"],
                    "shipZipCode":"12345",
                    "shipCountry":"INDONESIA" if record['partner_shipping_id']["country_id"]["name"] == False else record['partner_shipping_id']["country_id"]["name"],
#                     "shipCountry":"" if record['partner_shipping_id']["country_id"] == False else record['partner_shipping_id']["country_id"],
                    "shipZone":"NA",
                    "shipRoute":"NA",
                    "shipArea":"SHIP",
                    "remark2":"",
                    "remark1":"",
                    "allocatequantityOrder":"TRUE",
                    "shipInFull":"FALSE",
                    "orderLine": so_lines

                }
            ]
        }
        
        # The header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'SO'
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
        
        # Post API request
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        """if is_error == False:
            api_log['status'] = 'success'
        elif '"returnStatus":"-1"' in api_log['response_msg']:
            api_log['status'] = 'error'
        else:
            api_log['status'] = 'success'"""
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })

# STOCK PICKING FOR RETURNS ===================================================================
class ApiControllerStockPicking(models.Model):
    _inherit ='stock.picking'
    
    # PO RETURN (DW_PO_RET) (receive item -> return to vendor) using DW_SO API JSON format =======================================
    def api_return_po(self, record):
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createso"
        
        # A variable to store x_wms_rec_no value
        wms_no = ""
        # Not used
        line_no = 1
        # A variable to store purchase order lines to be returned
        item_lines = []
        # A variable to store the origin of the return's stock picking
        origin_name = ""
        # A variable to store partner_id value from a PO
        partner_shipping = request.env['res.partner']
        
        # Loop through all stock moves (PO lines from stock.picking.move_ids_without_package)
        for line in record.move_ids_without_package:
            
            # If there is a line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue
            
            #validasi partial apa engga
            
            #Checking where the return is partial or not
            
            is_partial_return = False
            
            # Create order line
            item_line = {
                "soLineOptChar1": line['x_studio_opt_char_1'],
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrder": str(int(line['product_uom_qty'])),
                # "originalOrderUOM": line['product_uom']['name'],
                "originalOrderUOM": "PCS",
                "lotNo": "LOT", 
                "filterTransactionCode": "NM",
                # "filterTransactionCode": str(line['x_studio_stock_product_code']),
                "soLineOptChar2": ""
            }
            # Not used
            line_no += 1
            # Append the current order line to the item_lines array
            item_lines.append(item_line)
            
            # Get the origin stock picking ===
            origin_name = record['origin'] # example: Return of WH/IN/00009
            origin_name = origin_name[10:] # example: WH/IN/00009
            source_sp = request.env['stock.picking'].search([('name', '=', origin_name)], limit=1) #Get WH/IN/00009
            
            # Loop through the “source_sp” variable
            # We need to loop because the search result returns a result set and not one record
            for pick in source_sp:
                # Example -> origin_name = WH/IN/00009.origin, wms_no = WH/IN/00009.x_wms_rec_no
                origin_name = pick.origin
                wms_no = pick.x_wms_rec_no
                
            # Get the partner id for this PO return ===
            # Search for the origin purchase order using the “origin_name” variable
            source_po = request.env['purchase.order'].search([('name', '=', origin_name)])
            # Assign a purchase order model to a variable called “po_record”
            po_record = request.env['purchase.order']
            
            # Loop through the “source_po” variable
            # We need to loop because the search result returns a result set and not one record
            for po in source_po:
                # Assign “source_po” to “po_record”
                # This way, we can access the individual record inside source_po
                po_record = po
            # Assign the value of po_record.partner_id to the “partner_shipping” variable
            partner_shipping = po_record.partner_id
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        # reference -> origin name ganti ke yg wh/out karena ini outbound
        # tambahin payload baru otherRemarks untuk simpen si origin_name
        payload = {"accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
            "namespace": "http://www.boonsoftware.com/createSO/POV",
            "order":[
                {
                    "customerPO":"",
                    "reference": record['name'],
                    "soHeaderOptChar1": wms_no,
                    "customerCode":"" if partner_shipping['x_studio_customer_id'] == False else partner_shipping['x_studio_customer_id'],
                    "soHeaderOptChar3":"",
                    "documentTransCode":"POR",
                    "orderDate":"" if record['create_date'] == False else datetime.strftime(record['create_date'], '%d/%m/%Y'),
                    "requestedDeliveryDate":"",
                    "ownerCode":"PRIMAVISTA",
                    "warehouseCode": "AVI",
                    "shipNo": "" if partner_shipping['x_studio_customer_id'] == False else partner_shipping['x_studio_customer_id'],
                    "shipAddress1":"" if partner_shipping["street"] == False else partner_shipping["street"],
                    "shipCity":"" if partner_shipping["city"] == False else partner_shipping["city"],
#                     "shipNo": "" if record['partner_shipping_id']['x_studio_customer_id'] == False else record['partner_shipping_id']['x_studio_customer_id'],
#                     "shipAddress1":"" if record['partner_shipping_id']["street"] == False else record['partner_shipping_id']["street"],
#                     "shipCity":"" if record['partner_shipping_id']["city"] == False else record['partner_shipping_id']["city"],
                    "shipZipCode":"12345",
#                     "shipCountry":"" if record['partner_shipping_id']["country_id"]["name"] == False else record['partner_shipping_id']["country_id"]["name"],
                    "shipCountry":"" if partner_shipping["country_id"]["name"] == False else partner_shipping["country_id"]["name"],
                    "shipZone":"NA",
                    "shipRoute":"NA",
                    "shipArea":"SHIP",
                    "otherReferences": origin_name,
                    "remark2":"",
                    "remark1":"",
                    "allocatequantityOrder":"TRUE",
                    "shipInFull":"FALSE",
                    "orderLine": item_lines

                }
            ]
        }
        
        # Create the header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'PO_RET'
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
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })

    
    # SO RETURN (DW_SO_RET) (sell item to customer -> return to us) using DW_SO API JSON format =================================
    def api_return_so(self, record):
        
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createasn"
        
        # line_no = 1
        
        # To store sale order lines to be returned
        po_lines = []
        # To store the origin of the return’s stock picking
        return_origin = ""
        # To store the origin of the return’s stock picking
        origin_name = ""
        # To store x_wms_rec_no value
        wms_no = ""
        # To store document trans code value (NOT NEEDED)
        doc_trans_code = ""
        # To store the partial or full validation
        is_partial = False
        
        # Loop through all stock moves
        for line in record['move_ids_without_package']:
            # If there is a line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue
            
            # Create order line
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrdered": str(line['product_qty']),
                # "uomCode": line['product_uom']['name'],
                "uomCode": "PCS",
                "stockStatusCode": "NM" if line['x_stock_status_code']  == False else line['x_stock_status_code']
                # "stockStatusCode": str(line['x_studio_stock_product_code'])
            }
            # line_no += 1
            
            # Append the current order line to the item_lines array
            po_lines.append(po_line)

            # Get the origin of the return's stock picking
            return_origin = record['origin'] # example: Return of WH/IN/00009
            return_origin = return_origin[10:] # example: WH/IN/00009
            # Get the origin stock picking by searching through the stock.picking model
            source_sp = request.env['stock.picking'].search([('name', '=', return_origin)], limit=1) #Get WH/IN/00009
            # source_sp_line = source_sp.move_line_ids_without_package
            
            # raise UserError(source_sp_line)

            # Loop through the “source_sp” variable
            # We need to loop because the search result returns a result set and not one record
            for pick in source_sp:
                # Assign the value of the origin stock picking’s origin to the “origin_name” variable
                origin_name = pick.origin # WH/IN/00009.origin = soNo nya
                # Assign the value of the origin stock picking’s x_wms_rec_no to the “wms_no” variable
                wms_no = pick.x_wms_rec_no # WH/IN/00009.x_wms_rec_no = wms rec no utk diassign ke doNo
        
        # Create payload --di payload sini, no po nya diganti sm wh/in hrsnya karena inbound trus yang origin_name itu no po -> masukin ke other remarks
        
        
        # Validation if the return is full or partial order
            payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {
                    "ownerReferences": "",
                    "poNo": record['name'], 
                    "supplierReferences": "", 
                    "sender": "",
                    "documentTransCode": "GRN", 
                    "ownerCode": "PRIMAVISTA",
                    "warehouseCode": "AVI",
                    # "poDate": po_date, # datetime.strftime(record['date_approve'],'%d/%m/%Y')
                    "poDate": "" if record['create_date'] == False else datetime.strftime(record['create_date'], '%d/%m/%Y'),
                    # "expectedArrivalDate": arrival_date, # datetime.strftime(record['date_planned'],'%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['scheduled_date'] == False else datetime.strftime(record['scheduled_date'], '%d/%m/%Y'),
                    "otherReferences": origin_name,
                    "remark1": "",
                    "doNo": wms_no, #wms_no,
                    # "ownerReferences":"",
                    # "poNo":"15220014721",
                    # "supplierReferences":"V-80",
                    # "sender":"VITA HEALTH INDONESIA, PT",
                    # "documentTransCode":"PODR",
                    # "ownerCode":"VITAHEALTH",
                    # "warehouseCode":"AVI",
                    # "poDate":"13-07-2022",
                    # "expectedArrivalDate":"13-07-2022",
                    # "otherReferences":"STCK TRS APL",
                    # "remark1":" Stock Transfer from APL 29 Jun'22\rSurat Jalan No: 9910278722, 9910278725, 9910278745, 9910278771, 9910278722",
                    # "doNo":"",
                    "asnLine": po_lines
                }
            ]
        }
        
        # Create the header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'SO_RET'
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
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        """if is_error == False:
            api_log['status'] = 'success'
        elif '"returnStatus":"-1"' in api_log['response_msg']:
            api_log['status'] = 'error'
        else:
            api_log['status'] = 'success'"""
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })
        
# CUSTOMER  ==========================================================================
class ApiControllerPartner(models.Model):
    _inherit = "res.partner"
    
    def api_dw_customer(self, record):
            
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createcustomer"
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "customer": [
                {
                    "ownerCode": "PRIMAVISTA",
                    "custCode": "" if record['x_studio_customer_id'] == False else record['x_studio_customer_id'],
                    "name": "" if record['name'] == False else record['name'],
                    "custGroup": "" if record['x_studio_customer_group'] == False else record['x_studio_customer_group'],
                    "address1": "" if record['street'] == False else record['street'],
                    "city": "" if record['city'] == False else record['city'],
                    "state": "DKI JAKARTA" if record['state_id']['name'] == False else str(record['state_id']['name']).upper(),
                    "zipCode": "12345" if record['zip'] == False else record['zip'],
                    "country": "" if record['country_id']['name'] == False else record['country_id']['name'],
                    "route": "NA",
                    "zone": "NA",
                    "custType": "IO",
                    "slsmnCode": "JLK",
                    "taxCode": "NA",
                    "termCode": "NA"
                }
            ]
        }
        
        # Create the header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'CUST'
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
                'company_id': self.env.context['allowed_company_ids'][0],
                'res_id': api_log['id'],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
        
        # Post the API request
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        """if is_error == False:
            api_log['status'] = 'success'
        elif '"returnStatus":"-1"' in api_log['response_msg']:
            api_log['status'] = 'error'
        else:
            api_log['status'] = 'success'"""
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })

# PRODUCT  ==========================================================================
class ApiControllerProduct(models.Model):
    _inherit = "product.template"
    
    def api_dw_product(self, record):
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-prd-symphony-api/createproduct"
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxODg1MTY2NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxODkzODA2NH0.KKTJME6GO_f4bP86fChza2tHXvDxKeXquJmEoGJtpUA",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "product": [
                {
                    "ownerCode": "PRIMAVISTA",
                    "warehouseCode": "AVI",
                    "product": "" if record['default_code'] == False else record['default_code'],
                    "desc1": "" if record['name'] == False else record['name'],
                    "brandName": "",
                    "baseUOM": "" if record['uom_id']['name'] == False else str(record['uom_id']['name']).upper(),
                    "prodGroup": "NA",
                    "subPrdGrp": "NA",
                    "storageType": "AB-RACK",
                    "altStorageType": "AB-BULK",
                    "wholeUOM": "" if record['uom_id']['name'] == False else str(record['uom_id']['name']).upper(),
                    "wholeDenomination": "" if record['uom_id']['ratio'] == False else str(int(record['uom_id']['ratio'])),
                    "palletDeno": "100",
                    "volume": "1",
                    "weight": "1",
                    "length": "",
                    "breadth": "",
                    "height": "",
                    "archived": "" if record['active'] == False else record['active'],
                    "prodStatus": "N",
                    "inbLeadtime2expiry": "",
                    "leadtime2expiry": "",
                    "shelfLife": "",
                    "issueType": "1",
                    "lotNoCtrl": "" if record['tracking'] == False else record['tracking'],
                    "autoSerial": "",
                    "expDateCtrl": "",
                    "palletCtrl": "",
                    "capSerialOut": "",
                    "price": "" if record['standard_price'] == False else record['standard_price']
                }
            ]
        }
        
        # Create the header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': payload,
                'message_type': 'PROD'
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
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        """if is_error == False:
            api_log['status'] = 'success'
        elif '"returnStatus":"-1"' in api_log['response_msg']:
            api_log['status'] = 'error'
        else:
            api_log['status'] = 'success'"""
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })