# -*- coding: utf-8 -*-

from odoo import models, fields, api
from openerp.osv import osv
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
from datetime import datetime
from odoo import http
import requests
from odoo.exceptions import UserError

# override stock move create when PO is confirmedd
class PurchaseOrderLineExt(models.Model):
    _inherit = 'purchase.order.line'
    x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')

#     @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLineExt, self)._prepare_stock_moves(picking)
        for rec in res:
            rec['x_studio_opt_char_1'] = self.x_studio_opt_char_1
        return res

# set the x studio opt char value in stock move based on the value from PO and SO line
class StockRuleExt(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(StockRuleExt, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
        return res
    
    @api.model
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        group_id = False
        res = super(StockRuleExt, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        
        res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
        return res

class CalendarEventExt(models.Model):
    _inherit = 'calendar.event'
    x_studio_latitude = fields.Float('Location Latitude', compute = '_compute_lat_long')
    x_studio_longitude = fields.Float('Location Longitude', compute = '_compute_lat_long')
    
    def action_test(self):
        x = requests.get('https://w3schools.com')
        curr_loc = self.location
        
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Warning'),
                'message': 'You cannot do this action now',
                'sticky': True,
            }
        }
        return notification
#         APIKey = 'AIzaSyBH4JCdioG8uH8HVtHJLwucbbiHxtRNMPE'
#         base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
#         endpoint = f"{base_url}?address={curr_loc}&key={APIKey}"
#         r = requests.get(endpoint)
#         if r.status_code not in range(200,299):
#             return None,None
# #         try:
#         results = r.json()['results'][0]
#         lat = results['geometry']['location']['lat']
#         lng = results['geometry']['location']['lng']
#         except:
#             pass
#         return lat, lng
    
    @api.depends('location')
    def _compute_lat_long(self):
        for rec in self:
            if rec.location:
                rec.x_studio_latitude = 10
                rec.x_studio_longitude = 20
            else:
                rec.x_studio_latitude = None
                rec.x_studio_longitude = None

class StockMoveExt(models.Model):
    _inherit = 'stock.move'
    x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')

# override create stock move when SO is confirmed
class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'
    x_studio_line_no = fields.Char('x_studio_line_no')
    
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLineExt, self)._prepare_procurement_values(group_id)
        res.update({'x_studio_opt_char_1': self.x_studio_line_no})
        return res

# set the wms rec no value in stock picking when the return button is clicked in a DO or PO RCPT
class StockReturnPickingExt(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    @api.model
    def _create_returns(self):
        new_picking, pick_type_id = super(StockReturnPickingExt, self)._create_returns()
        
        # Search for the new picking
        curr_pick = request.env['stock.picking'].search([('id', '=', int(new_picking))], limit=1)
    
        # Get the stock.picking source name
        trans_code = ""
        in_num = curr_pick.origin
        in_num = in_num[10:]
        if "IN" in in_num:
            trans_code = "POR"
        else:
            trans_code = "GRA"
        
        
        # Get the source stock.picking (origin)
        source = request.env['stock.picking'].search([('name', '=', in_num)], limit=1)
        
        # Set current stock.picking x_wms_rec_no to source stock.picking's (loop is mandatory as search returns ResultSet not one 
        # record)
        wms_no = 0
        
        for pick in source:
            wms_no = pick.x_wms_rec_no

        
        curr_pick.write({'x_wms_rec_no': wms_no, 'x_studio_doc_trans_code':trans_code})
        curr_pick.move_lines.write({'x_wms_rec_no': wms_no})
        curr_pick.move_lines.move_line_ids.write({'x_wms_rec_no': wms_no})
        return new_picking, pick_type_id
    
# API VEN MODEL ==========================================================================
class api_ven(models.Model):
    _name = 'api_ven.api_ven'
    _description = 'api_ven.api_ven'
    
    # for the changes to take effect, upgrade the API VEN module in apps 
    name = fields.Char(string="Message ID", required=True, copy=False, readonly=True, index=True, default=lambda self: ('New'))
    incoming_msg = fields.Text(string="Incoming Message")
    response_msg = fields.Text(string="Response Message")
    status = fields.Selection([('new','New'),('process','Processing'),('success','Success'),('error','Error')])
    created_date = fields.Datetime(string="Created Date")
    response_date = fields.Datetime(string="Response Date")
    message_type = fields.Selection([('RCPT','CRT_RCPT'),('DO','CRT_DO'),('PO','DW_PO'),('SO','DW_SO'),('PO_RET','DW_PO_RET'),('SO_RET','DW_SO_RET'),('RCPT_RET','CRT_RCPT_RET'),('DO_RET','CRT_DO_RET'),('CUST','DW_CUST'),('PROD','DW_PROD')])
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

    
    
    
# PURCHASE ORDER ==========================================================================
class ApiController(models.Model):
    _inherit = "purchase.order"
    
    def api_dw_po(self, record):
            
        # PROSES KIRIM API
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        # PO_LINES: Contains every product in the PO
        line_no = 1
        po_lines = []
        
        for line in record['order_line']:
            line['x_studio_opt_char_1'] = str(line_no)
            
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrdered": str(line['product_qty']),
#                 "uomCode": line['product_uom']['name'],
                "uomCode": "PCS",
                "stockStatusCode": "NM"
            }
            line_no += 1
            
            po_lines.append(po_line)
        
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {
                    "ownerReferences": "",
                    "poNo": "" if record['name'] == False else record['name'],
                    "supplierReferences": "" if record['partner_ref'] == False else record['partner_ref'],
                    "sender": "",
#                     "documentTransCode": "PODR",
                    "documentTransCode":"" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
                    "ownerCode": "PRIMAVISTA",
#                     "warehouseCode": "" if record['picking_type_id']['warehouse_id']['code'] == False else record['picking_type_id']['warehouse_id']['code'],
                    "warehouseCode": "AVI",
                    "poDate": "" if record['date_approve'] == False else datetime.strftime(record['date_approve'], '%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['date_planned'] == False else datetime.strftime(record['date_planned'], '%d/%m/%Y'),
                    "otherReferences": "",
                    "remark1": "",
                    "doNo": "",
#                     "ownerReferences":"",
#                     "poNo":"15220014721",
#                     "supplierReferences":"V-80",
#                     "sender":"VITA HEALTH INDONESIA, PT",
#                     "documentTransCode":"PODR",
#                     "ownerCode":"VITAHEALTH",
#                     "warehouseCode":"AVI",
#                     "poDate":"13-07-2022",
#                     "expectedArrivalDate":"13-07-2022",
#                     "otherReferences":"STCK TRS APL",
#                     "remark1":" Stock Transfer from APL 29 Jun'22\rSurat Jalan No: 9910278722, 9910278725, 9910278745, 9910278771, 9910278722",
#                     "doNo":"",
                    "asnLine": po_lines
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        # Create log
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
        
#        try:
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
#        except Exception as e:
#            is_error = True
#            api_log['status'] = 'error'
            
#        wms_response = base64.b64encode(bytes(str(r.text), 'utf-8'))
        
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
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
#         r = requests.post(apiurl, data=json.dumps(payload), headers=headers)





# SALES ORDER ==========================================================================        
class ApiControllerSO(models.Model):
    _inherit = "sale.order"
    
    def api_dw_so(self, record):
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createso"
        
        line_no = 1
        so_lines = []
        
        # so_lines = every items in the SO
        for line in record['order_line']:
            line['x_studio_line_no'] = str(line_no)
            
            so_line = {
                "soLineOptChar1": line['x_studio_line_no'],
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrder": str(int(line['product_uom_qty'])),
#                 "originalOrderUOM": line['product_uom']['name'],
                "originalOrderUOM": "PCS",
                "lotNo": "LOT", 
                "filterTransactionCode": "NM",
                "soLineOptChar2": ""
            }
            line_no += 1
            
            so_lines.append(so_line)
        
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createSO/POV",
            "order":[
                {
                    "customerPO":"",
                    "reference":"" if record['name'] == False else record['name'],
                    "customerCode":"" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
                    "soHeaderOptChar3":"",
                    "documentTransCode":"" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'],
#                     "documentTransCode":"OR", 
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
                    "shipCountry":"" if record['partner_shipping_id']["country_id"]["name"] == False else record['partner_shipping_id']["country_id"]["name"],
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
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create log
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
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
        
#         r = requests.post(apiurl, data=json.dumps(payload), headers=headers)




# STOCK PICKING FOR RETURNS ===================================================================
class ApiControllerStockPicking(models.Model):
    _inherit ='stock.picking'
    
    # Returning a PO (receive item -> return to vendor) using SO format =======================================
    def api_return_po(self, record):
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createso"
        
        wms_no = 0
        line_no = 1
        item_lines = []
        origin_name = ""
        partner_shipping = request.env['res.partner']
        
        # Return PO lines from stock.picking.move_ids_without_package
        for line in record.move_ids_without_package:
            item_line = {
                "soLineOptChar1": line['x_studio_opt_char_1'],
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrder": str(int(line['product_uom_qty'])),
#                 "originalOrderUOM": line['product_uom']['name'],
                "originalOrderUOM": "PCS",
                "lotNo": "LOT", 
                "filterTransactionCode": "NM",
                "soLineOptChar2": ""
            }
            line_no += 1
            
            item_lines.append(item_line)
            
            # Searching for Origin and WMS receipt No from PO confirm====
            origin_name = record['origin'] #Return of WH/IN/00009
            origin_name = origin_name[10:] #WH/IN/00009
            source_sp = request.env['stock.picking'].search([('name', '=', origin_name)], limit=1) #Get WH/IN/00009
            
#           origin_name = WH/IN/00009.origin, wms_no = WH/IN/00009.x_wms_rec_no
            for pick in source_sp:
                origin_name = pick.origin
                wms_no = pick.x_wms_rec_no
                
            # Searching for partner_shipping ===
            source_po = request.env['purchase.order'].search([('name', '=', origin_name)])
            po_record = request.env['purchase.order']
            for po in source_po:
                po_record = po
            partner_shipping = po_record.partner_id
        
        payload = {"accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createSO/POV",
            "order":[
                {
                    "customerPO":"",
                    "reference":origin_name,
                    "receiptNo": wms_no,
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
                    "remark2":"",
                    "remark1":"",
                    "allocatequantityOrder":"TRUE",
                    "shipInFull":"FALSE",
                    "orderLine": item_lines

                }
            ]
        }
        
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create log
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
        
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        api_log['response_msg'] = base64.b64encode(bytes(str(r.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        if r.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })

        
        

    # Returning a SO (sell item -> return to us) using PO format =======================================
    def api_return_so(self, record):
        # PROSES KIRIM API
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        # PO_LINES: Contains every product in the PO
#         line_no = 1
        po_lines = []
        return_origin = ""
        origin_name = ""
        wms_no = 0
        doc_trans_code = ""
        
        for line in record['move_ids_without_package']:
            # line['x_studio_opt_char_1'] = str(line_no)
            
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": line['product_id']["product_tmpl_id"]["default_code"],
                "quantityOrdered": str(line['product_qty']),
#                 "uomCode": line['product_uom']['name'],
                "uomCode": "PCS",
                "stockStatusCode": "NM"
            }
            # line_no += 1
            po_lines.append(po_line)

            return_origin = record['origin'] #Return of WH/IN/00009
            return_origin = return_origin[10:] #WH/IN/00009
            source_sp = request.env['stock.picking'].search([('name', '=', return_origin)], limit=1) #Get WH/IN/00009

            for pick in source_sp:
                origin_name = pick.origin # WH/IN/00009.origin = soNo nya
                wms_no = pick.x_wms_rec_no # WH/IN/00009.x_wms_rec_no = wms rec no utk diassign ke doNo
        
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "namespace": "http://www.boonsoftware.com/createASN/POV",
            "asn": [
                {
                    "ownerReferences": "",
                    "poNo": origin_name, 
                    "supplierReferences": "", 
                    "sender": "",
                    "documentTransCode": "GRA", 
                    "ownerCode": "PRIMAVISTA",
                    "warehouseCode": "AVI",
#                     "poDate": po_date, # datetime.strftime(record['date_approve'],'%d/%m/%Y')
                    "poDate": "" if record['create_date'] == False else datetime.strftime(record['create_date'], '%d/%m/%Y'),
#                     "expectedArrivalDate": arrival_date, # datetime.strftime(record['date_planned'],'%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['scheduled_date'] == False else datetime.strftime(record['scheduled_date'], '%d/%m/%Y'),
                    "otherReferences": "",
                    "remark1": "",
                    "doNo": "", #wms_no,
#                     "ownerReferences":"",
#                     "poNo":"15220014721",
#                     "supplierReferences":"V-80",
#                     "sender":"VITA HEALTH INDONESIA, PT",
#                     "documentTransCode":"PODR",
#                     "ownerCode":"VITAHEALTH",
#                     "warehouseCode":"AVI",
#                     "poDate":"13-07-2022",
#                     "expectedArrivalDate":"13-07-2022",
#                     "otherReferences":"STCK TRS APL",
#                     "remark1":" Stock Transfer from APL 29 Jun'22\rSurat Jalan No: 9910278722, 9910278725, 9910278745, 9910278771, 9910278722",
#                     "doNo":"",
                    "asnLine": po_lines
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create log
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
        
#        try:
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
#        except Exception as e:
#            is_error = True
#            api_log['status'] = 'error'
            
#        wms_response = base64.b64encode(bytes(str(r.text), 'utf-8'))
        
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
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
        

        
        
# CUSTOMER  ==========================================================================
class ApiController(models.Model):
    _inherit = "res.partner"
    
    def api_dw_customer(self, record):
            
#       PROSES KIRIM API (DIGANTI JADI APA ????????????????)
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "customer": [
                {
                    "ownerCode": "PRIMAVISTA",
                    "custCode": "" if record['x_studio_customer_id'] == False else record['x_studio_customer_id'],
                    "name": "" if record['name'] == False else record['name'],
                    "custGroup": "" if record['x_studio_customer_group'] == False else record['x_studio_customer_group'],
                    "address1": "" if record['street'] == False else record['street'],
                    "city": "" if record['city'] == False else record['city'],
                    "state": "" if record['state_id']['name'] == False else record['state_id']['name'],
                    "zipCode": "" if record['zip'] == False else record['zip'],
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
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create log
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
        
#        try:
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
#        except Exception as e:
#            is_error = True
#            api_log['status'] = 'error'
            
#        wms_response = base64.b64encode(bytes(str(r.text), 'utf-8'))
        
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
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
        
        
        
        
# PRODUCT  ==========================================================================
class ApiController(models.Model):
    _inherit = "product.template"
    
    def api_dw_product(self, record):
            
#       PROSES KIRIM API (DIGANTI JADI APA ????????????????)
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
#             "namespace": "http://www.boonsoftware.com/createASN/POV",
            "product": [
                {
                    "ownerCode": "PRIMAVISTA",
                    "warehouseCode": "AVI",
                    "product": "" if record['default_code'] == False else record['default_code'],
                    "desc1": "",
                    "brandName": "",
                    "baseUOM": "",
                    "prodGroup": "NA",
                    "subPrdGrp": "NA",
                    "storageType": "AB-RACK",
                    "altStorageType": "AB-BULK",
                    "wholeUOM": "",
                    "wholeDenomination": "",
                    "palletDeno": "100",
                    "volume": "1",
                    "weight": "1",
                    "length": "",
                    "breadth": "",
                    "height": "",
                    "archived": "",
                    "prodStatus": "N",
                    "inbLeadtime2expiry": "",
                    "leadtime2expiry": "",
                    "shelfLife": "",
                    "issueType": "1",
                    "lotNoCtrl": "",
                    "autoSerial": "",
                    "expDateCtrl": "",
                    "palletCtrl": "",
                    "capSerialOut": "",
                    "price": ""
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        #Create log
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
        
#        try:
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
#        except Exception as e:
#            is_error = True
#            api_log['status'] = 'error'
            
#        wms_response = base64.b64encode(bytes(str(r.text), 'utf-8'))
        
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
        
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(r.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })

