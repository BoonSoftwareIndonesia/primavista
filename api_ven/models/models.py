# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64
from datetime import datetime
from odoo import http


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

class api_ven(models.Model):
    _name = 'api_ven.api_ven'
    _description = 'api_ven.api_ven'
    
    name = fields.Char(string="Message ID", required=True, copy=False, readonly=True, index=True, default=lambda self: ('New'))
    incoming_msg = fields.Text(string="Incoming Message")
    response_msg = fields.Text(string="Response Message")
    status = fields.Selection([('new','New'),('process','Processing'),('success','Success'),('error','Error')])
    created_date = fields.Datetime(string="Created Date")
    response_date = fields.Datetime(string="Response Date")
    message_type = fields.Selection([('RCPT','CRT_RCPT'),('DO','CRT_DO')])
    incoming_txt = fields.Many2one('ir.attachment', string="Incoming txt", readonly=True)
    response_txt = fields.Many2one('ir.attachment', string="Response txt", readonly=True)
    raw_data = fields.Binary(string="Raw Data", attachment=True)
    raw_dataname = fields.Char(string="File Name")
    
    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == ('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('api.seq') or ('New')
        result = super(api_sbt_inv, self).create(vals)
        return result
    
class ApiController(models.Model):
    _inherit = "purchase.order"
    
    def api_dw_po(self, record):
            
#       PROSES KIRIM API
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createasn"
        
        line_no = 1
        po_lines = []
        
        for line in record['order_line']:
            line['x_studio_opt_char_1'] = str(line_no)
            
            po_line = {
                "inwardLineOptChar1": line['x_studio_opt_char_1'],
                "inwardLineOptChar2": "",
                "product": record['product_id']['name'],
                "quantityOrdered": str(line['product_qty']),
                "uomCode": line['product_uom']['name'],
                "stockStatusCode": "" if line['x_studio_stock_status_code'] == False else line['x_studio_stock_status_code']
            }
            line_no += 1
            
            po_lines.append(po_line)
        
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "asn": [
                {
                     
                    "ownerReferences": "",
                    "poNo": "" if record['name'] == False else record['name'],
                    "supplierReferences": "" if record['partner_ref'] == False else record['partner_ref'],
                    "sender": "",
                    "documentTransCode": "" if record['x_studio_document_trans_code'] == False else record['x_studio_document_trans_code'],
                    "ownerCode": "" if record['x_studio_owner'] == False else record['x_studio_owner'],
                    "warehouseCode": "" if record['picking_type_id']['warehouse_id']['code'] == False else record['picking_type_id']['warehouse_id']['code'],
                    "poDate": "" if record['date_approve'] == False else datetime.strftime(record['date_approve'], '%d/%m/%Y'),
                    "expectedArrivalDate": "" if record['date_planned'] == False else datetime.strftime(record['date_planned'], '%d/%m/%Y'),
                    "otherReferences": "",
                    "remark1": "",
                    "doNo": "",
                    "asnLine": po_lines
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)
        
        #Create log
#         try:
#             api_log = self.env['api_ven.api_ven'].create({
#                 'status': 'new',
#                 'created_date': datetime.now(),
#                 'incoming_msg': 'test',
#                 'message_type': 'RCPT'
#             })

#             api_log['status'] = 'process'
#         except:
#             error['Error'] = str(e)
#             is_error = True
        
class ApiControllerSO(models.Model):
    _inherit = "sale.order"
    
    def api_dw_so(self, record):
        apiurl = "https://cloud1.boonsoftware.com/avi-trn-symphony-api/createso"
        
        line_no = 1
        so_lines = []
        
        for line in record['order_line']:
            line['x_studio_line_no'] = str(line_no)
            
            so_line = {
                "soLineOptChar1": line['x_studio_line_no'],
                "product": line['product_id']['default_code'],
                "quantityOrder": str(int(line['product_uom_qty'])),
                "originalOrderUOM": line['product_uom']['name'],
                "lotNo": "LOT",
                "filterTransactionCode": "NM",
                "soLineOptChar2": ""
            }
            line_no += 1
            
            so_lines.append(so_line)
        
        
        payload = {
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
            "order":[
                {
#                     "customerPO":"",
#                     "reference":"" if record['name'] == False else record['name'],
#                     "customerCode":"" if record['x_studio_customer_code'] == False else record['x_studio_customer_code'],
#                     "soHeaderOptChar3":"",
#                     "documentTransCode":"" if record['x_studio_document_trans_code'] == False else record['x_studio_document_trans_code'],
#                     "orderDate":"" if record['date_order'] == False else datetime.strftime(record['date_order'], '%d/%m/%Y'),
#                     "requestedDeliveryDate":"",
#                     "ownerCode":"" if record['x_studio_owner_code'] == False else record['x_studio_owner_code'],
#                     "warehouseCode": "" if record['warehouse_id']['code'] == False else record['warehouse_id']['code'],
#                     "shipNo":"" if record['x_studio_internal_id'] == False else record['x_studio_internal_id'],
#                     "shipAddress1":"" if record['partner_shipping_id']["street"] == False else record['partner_shipping_id']["street"],
#                     "shipCity":"" if record['partner_shipping_id']["city"] == False else record['partner_id']["x_studio_internal_id"],
#                     "shipZipCode":"" if record['partner_shipping_id']["zip"] == False else record['partner_shipping_id']["zip"],
#                     "shipCountry":"" if record['partner_shipping_id']["country_id"]["name"] == False else record['partner_shipping_id']["country_id"]["name"],
#                     "shipZone":"NA",
#                     "shipRoute":"NA",
#                     "shipArea":"SHIP",
#                     "remark2":"",
#                     "remark1":"",
#                     "allocatequantityOrder":"TRUE",
#                     "shipInFull":"FALSE",
#                     "orderLine": so_lines
                    
                    "customerPO":"",
                    "reference":"" if record['name'] == False else record['name'],
                    "customerCode":"" if record['x_studio_customer_code'] == False else record['x_studio_customer_code'],
                    "soHeaderOptChar3":"",
                    "documentTransCode":"" if record['x_studio_document_trans_code'] == False else record['x_studio_document_trans_code'],
                    "orderDate":"" if record['date_order'] == False else datetime.strftime(record['date_order'], '%d/%m/%Y'),
                    "requestedDeliveryDate":"",
                    "ownerCode":"" if record['x_studio_owner_code'] == False else record['x_studio_owner_code'],
                    "warehouseCode": "" if record['warehouse_id']['code'] == False else record['warehouse_id']['code'],
                    "shipNo": "" if record['x_studio_internal_id'] == False else record['x_studio_internal_id'],
                    "shipAddress1":"" if record['partner_shipping_id']["street"] == False else record['partner_shipping_id']["street"],
                    "shipCity":"Banda Aceh",
                    "shipZipCode":"23229",
                    "shipCountry":"INDONESIA",
                    "shipZone":"NA",
                    "shipRoute":"NA",
                    "shipArea":"SHIP",
                    "remark2":"",
                    "remark1":"",
                    "allocatequantityOrder":"TRUE",
                    "shipInFull":"FALSE",
                    "orderLine": so_lines
                    
#                     "customerPO":"",
#                     "reference":"11220019401",
#                     "customerCode":"C01-0478",
#                     "soHeaderOptChar3":"",
#                     "documentTransCode":"OR",
#                     "orderDate":"15-07-2022",
#                     "requestedDeliveryDate":"",
#                     "ownerCode":"OMRON",
#                     "warehouseCode":"AVI",
#                     "shipNo":"0478",
#                     "shipAddress1":"Jl. Residen Danu Broto. Desa Geuceu Kayee Jato. Dusun Taman Mulia. Gang Mawar No 33,",
#                     "shipCity":"Banda Aceh",
#                     "shipZipCode":"23229",
#                     "shipCountry":"INDONESIA",
#                     "shipZone":"NA",
#                     "shipRoute":"NA",
#                     "shipArea":"SHIP",
#                     "remark2":"",
#                     "remark1":"",
#                     "allocatequantityOrder":"TRUE",
#                     "shipInFull":"FALSE",
#                     "orderLine": so_lines
#                                 [
#                                     {
#                                        "soLineOptChar1":"2",
#                                        "product":"HEM-7121",
#                                        "quantityOrder":"1",
#                                        "originalOrderUOM":"BOX",
#                                        "lotNo":"%",
#                                        "filterTransactionCode":"NM",
#                                        "soLineOptChar2":"OR"
#                                     }
#                                 ]

                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)