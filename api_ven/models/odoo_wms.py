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

class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'
    x_studio_doc_trans_code = fields.Selection([("PODR", "PODR"),],string="Doc Trans Code", default='PODR')

# Override for PO and SO return ======================
# Override stock move creation process when a PO is confirmed. 
# This prepares the stock moves data for one order line and returns a list of dictionary ready to be used in stock.move's create()
# So we can set the stock move's x_studio_opt_char_1 value with the value from the corresponding PO line's x_studio_opt_char_1
class PurchaseOrderLineExt(models.Model):
    _inherit = 'purchase.order.line'
    x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')
    x_stock_status_code = fields.Selection([("NM", "Normal"),("DM", "Damage"),("ED","Expired"),("OBS","Obsolette"),("PR","Product Recall"),("RJCT","Reject"),],string="Stock Status Code", default='NM')

    # @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLineExt, self)._prepare_stock_moves(picking)
        for rec in res:
            rec['x_studio_opt_char_1'] = self.x_studio_opt_char_1
        return res

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'
    x_studio_doc_trans_code = fields.Selection([("OR", "OR"),("SMPL", "SAMPLE"),("ORD","ORD"),("FOC","FOC"),("COSN OUT","COSN OUT"),("CONS","CONS"),("Adjustment GI","Adjustment GI"),("POR","POR")],string="Doc Trans Code", default='OR')

# Override stock move creation process when a SO is confirmed. 
# This prepares the stock moves data for one order line and returns a list of dictionary ready to be used in stock.move's create()
# So we can set the stock move's x_studio_opt_char_1 value with the value from the corresponding SO line's x_studio_line_no
class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'
    x_studio_line_no = fields.Char('x_studio_line_no')
    x_stock_status_code = fields.Selection([("NM", "Normal"),("DM", "Damage"),("ED","Expired"),("OBS","Obsolette"),("PR","Product Recall"),("RJCT","Reject"),],string="Stock Status Code", default='NM')
    lot_record_id = fields.Many2one("lot_record.lot_record", domain="[('product_id', '=', product_id)]", string="Lot")
    
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLineExt, self)._prepare_procurement_values(group_id)
        res.update({'x_studio_opt_char_1': self.x_studio_line_no})
        return res

# Adding new variable which is x_stock_status_code in stock.move.line
class StockMoveLineExt(models.Model):
    _inherit = 'stock.move.line'
    x_stock_status_code = fields.Selection([("NM", "Normal"),("DM", "Damage"),("ED","Expired"),("OBS","Obsolette"),("PR","Product Recall"),("RJCT","Reject"),], string="Stock Status Code")
    x_wms_lot_records = fields.Char(string="Lot Number")

class StockPickingExt(models.Model):
    _inherit = 'stock.picking'
    x_studio_doc_trans_code = fields.Selection([("CONS-IN", "CONS-IN"),("EI", "EI"),("EXI","EXI"),("GR","GR"),("GRA","GRA"),("PODR","PODR"),("R","R"),("TRC-IN","TRC-IN"),("WHS-TRF","WHS-TRF"),("GRN","GRN"),("GRT","GRT"),("CONS-OUT","CONS-OUT"),("CP","CP"),("EO","EO"),("EXO","EXO"),("FOC","FOC"),("OCS","OCS"),("OR","OR"),("OSS","OSS"),("POR","POR"),("RTP","RTP"),("RTV","RTV"),("SMPL","SMPL"),("TRC-OUT","TRC-OUT"),], string="Doc Trans Code")

class UomExt(models.Model):
    _inherit = 'uom.uom'
    ratio = fields.Float('Combined Ratio', compute='_compute_ratio', inverse='_set_ratio', store=False, required=True)

# PURCHASE ORDER (DW_PO API) (Odoo to WMS) ==========================================================================
class POApiController(models.Model):
    _inherit = ['purchase.order']
    
    def api_dw_po(self, record):
            
        # The endpoint in wms (must change this to prd endpoint if we want to patch to prd)
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        # A variable to store the value of the current line number
        line_no = 1
        # An array to store the PO lines
        po_lines = []
        # To store the origin of this PO (the SO(s) that generated this PO)
        res = ""
        unique_res = ""
        owner_code = ""

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        
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
                "uomCode": "UNITS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
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
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {                    
                    "ownerReferences": "",
                    "poNo": "" if record['name'] == False else record['name'],
                    "supplierReferences": "" if record['partner_ref'] == False else record['partner_ref'],
                    "sender": "",
                    "documentTransCode":"PODR" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
                    "ownerCode": owner_code,
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

# SALES ORDER (DW_SO API) (Odoo to WMS) =================================================================     
class SOApiController(models.Model):
    _inherit = "sale.order"

    def api_dw_so(self, record):
        # The endpoint in wms (must change this to prd endpoint if we want to patch to prd)
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createso"
        
        # A variable to store the value of the current line number
        line_no = 1
        # A variable to store the SO lines
        so_lines = []

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        # raise UserError(f"owner code: {owner_code}")
        
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
                "originalOrderUOM": "UNITS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
                "lotNo": "LOT" if line['lot_record_id']['name'] == False else line['lot_record_id']['name'].upper(), 
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
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createSO/POV",
            "order":[
                {
                    "customerPO":"",
                    "reference":"" if record['name'] == False else record['name'],
                    "customerCode":"" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
                    "soHeaderOptChar3":"",
                    "documentTransCode":"OR" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
                    "orderDate":"" if record['date_order'] == False else datetime.strftime(record['date_order'], '%d/%m/%Y'),
                    "requestedDeliveryDate":"",
#                     "ownerCode":"" if record['x_studio_owner_code'] == False else record['x_studio_owner_code'],
                     "ownerCode": owner_code,
#                     "warehouseCode": "" if record['warehouse_id']['code'] == False else record['warehouse_id']['code'],
                    "warehouseCode": "AVI",
#                     "shipNo": "" if record['x_studio_internal_id'] == False else record['x_studio_internal_id'],
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
        
        # raise UserError(f"{r.text}")
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

# STOCK PICKING FOR RETURNS ===================================================================
class ApiControllerStockPicking(models.Model):
    _inherit ='stock.picking'
    
    # PO RETURN (DW_PO_RET) (receive item -> return to vendor) using DW_SO API JSON format
    # =======================================
    def api_return_po(self, record):
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createso"
        
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
        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        
        # Loop through all stock moves (PO lines from stock.picking.move_ids_without_package)
        for line in record.move_ids_without_package:
            
            # If there is a line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue

            if line['move_line_ids']['x_stock_status_code'] == False:
                line['move_line_ids']['x_stock_status_code'] = 'NM'
                
            #Checking where the return is partial or not
            is_partial_return = False

            # Create order line
            item_line = {
                "soLineOptChar1": line['x_studio_opt_char_1'],
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrder": str(int(line['product_uom_qty'])),
                "originalOrderUOM": "UNITS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
                "lotNo": "LOT" if line['move_line_ids']['x_wms_lot_records'] == False else line['move_line_ids']['x_wms_lot_records'].upper(), 
                "filterTransactionCode": line['move_line_ids']['x_stock_status_code'],
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
                
            # raise UserError(f"{source_sp}")
                
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
        payload = {"accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
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
                    "ownerCode":owner_code,
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
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
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
        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        
        # Loop through all stock moves
        for line in record['move_ids_without_package']:
            # If there is a line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue

            if line['move_line_ids']['x_stock_status_code'] == False:
                line['move_line_ids']['x_stock_status_code'] = 'NM'
            
            # Create order line
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrdered": str(line['product_qty']),
                "uomCode": "UNITS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
                "stockStatusCode": line['move_line_ids']['x_stock_status_code']
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
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {
                    "ownerReferences": "",
                    "poNo": record['name'], 
                    "supplierReferences": "", 
                    "sender": "",
                    "documentTransCode": "GRN", 
                    "ownerCode": owner_code,
                    "warehouseCode": "AVI",
                    # "poDate": po_date, # datetime.strftime(record['date_approve'],'%d/%m/%Y')
                    "poDate": "" if record['create_date'] == False else datetime.strftime(record['create_date'], '%d/%m/%Y'),
                    # "expectedArrivalDate": arrival_date, # datetime.strftime(record['date_planned'],'%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['scheduled_date'] == False else datetime.strftime(record['scheduled_date'], '%d/%m/%Y'),
                    "otherReferences": origin_name,
                    "remark1": "",
                    "doNo": wms_no,
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
        error = {}

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
            
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createcustomer"
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "customer": [
                {
                    "ownerCode": owner_code,
                    "custCode": "" if record['x_studio_customer_id'] == False else record['x_studio_customer_id'],
                    "name": "" if record['name'] == False else record['name'],
                    "custGroup": "" if record['x_studio_customer_group'] == False else record['x_studio_customer_group'],
                    "address1": "" if record['street'] == False else record['street'],
                    "address2": "" if record['street2'] == False else record['street2'],
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
            'mimetype': 'text/plain'
        })

    def api_dw_ship_no(self, record):
        
        error = {}

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"

        if not record.parent_id.x_studio_customer_id:  
            raise UserError("Please save customer or vendor first, or contact consultant")
            
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createship"
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "ship": [
                {
                    "ownerCode": owner_code,
                    "custCode": "" if record['parent_id']['x_studio_customer_id'] == False else record['parent_id']['x_studio_customer_id'],
        		    "shipNo": "" if record['x_studio_customer_id'] == False else record['x_studio_customer_id'],
                    "name": "" if record['name'] == False else record['name'],
                    "address1": "" if record['street'] == False else record['street'],
                    "city": "" if record['city'] == False else record['city'],
                    "state": "Jakarta" if record['state_id']['name'] == False else str(record['state_id']['name']).upper(),
                    "zipCode": "12345" if record['zip'] == False else record['zip'],
                    "country": "" if record['country_id']['name'] == False else record['country_id']['name'],
                    "route": "NA",
                    "zone": "NA"
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
                'message_type': 'SHIP'
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
            'mimetype': 'text/plain'
        })

# PRODUCT  ==========================================================================
class ApiControllerProduct(models.Model):
    _inherit = "product.template"
    
    def api_dw_product(self, record):
        # The endpoint in wms that must be changed to the prd endpoint if we want to patch to prd
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createproduct"

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        
        # Create payload
        # There is the access token for WMS, this needs to be changed to prd's access token if we want to patch to prd
        # There is also the rest of the data that will be sent to WMS. For this part, refer to the mapping documentation
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "product": [
                {
                    "ownerCode": owner_code,
                    "warehouseCode": "AVI",
                    "product": "" if record['default_code'] == False else record['default_code'],
                    "desc1": "" if record['name'] == False else record['name'],
                    "brandName": "NA" if record['x_product_brand'] == False else record['x_product_brand'],
                    "baseUOM": "" if record['uom_id']['name'] == False else str(record['uom_id']['name']).upper(),
                    "prodGroup": "NA" if record['categ_id']['parent_id']['name'] == False else str(record['categ_id']['parent_id']['name']).upper(),
                    "subPrdGrp": "NA" if record['categ_id']['name'] == False else str(record['categ_id']['name']).upper(),
                    "storageType": "AB-RACK",
                    "altStorageType": "AB-BULK",
                    "wholeUOM": "" if record['uom_id']['name'] == False else str(record['uom_id']['name']).upper(),
                    "wholeDenomination": "" if record['uom_id']['ratio'] == False else str(int(record['uom_id']['ratio'])),
                    "palletDeno": "100",
                    "volume": "1" if record['volume'] == 0 else str(record['volume']),
                    "weight": "1" if record['weight'] == 0 else str(record['weight']),
                    "length": "" if record['x_product_length'] == 0 else record['x_product_length'],
                    "breadth": "",
                    "height": "" if record['x_product_height'] == 0 else record['x_product_height'],
                    "archived": "" if record['active'] == False else record['active'],
                    "prodStatus": "N",
                    "inbLeadtime2expiry": "",
                    "leadtime2expiry": "",
                    "shelfLife": "",
                    "issueType": "1",
                    "lotNoCtrl": "TRUE" if record['x_is_lot_tracking'] == True else "",
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