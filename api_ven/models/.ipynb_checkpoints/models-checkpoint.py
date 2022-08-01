# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request
import json, datetime, requests
from datetime import datetime


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
                     
                    "ownerReferences": "N/A",
                    "poNo": "" if record['name'] == False else record['name'],
                    "supplierReferences": "V-80",
                    "sender": "N/A",
                    "documentTransCode": "PODR",
                    "ownerCode": "VITAHEALTH",
                    "warehouseCode": "AVI",
                    "poDate": "13-07-2022",
                    "expectedArrivalDate": "13-07-2022",
                    "otherReferences": "N/A",
                    "remark1": "N/A",
                    "doNo": "N/A",
                    "asnLine": po_lines
#                     "ownerReferences": "" if record['x_studio_owner_reference'] == False else record['x_studio_owner_reference'],
#                     "poNo": "" if record['name'] == False else record['name'],
#                     "supplierReferences": "" if record['partner_ref'] == False else record['partner_ref'],
#                     "sender": "" if record['x_studio_sender'] == False else record['x_studio_sender'],
#                     "documentTransCode": "" if record['x_studio_document_trans_code'] == False else record['x_studio_document_trans_code'],
#                     "ownerCode": "" if record['x_studio_owner'] == False else record['x_studio_owner'],
#                     "warehouseCode": "" if record['picking_type_id']['warehouse_id']['code'] == False else record['picking_type_id']['warehouse_id']['code'],
#                     "poDate": "" if record['date_approve'] == False else datetime.strftime(record['date_approve'], '%d/%m/%Y'),
#                     "expectedArrivalDate": "" if record['date_planned'] == False else datetime.strftime(record['date_planned'], '%d/%m/%Y'),
#                     "otherReferences": "" if record['x_studio_other_reference'] == False else record['x_studio_other_reference'],
#                     "remark1": "" if record['x_studio_remark_1'] == False else record['x_studio_remark_1'],
#                     "doNo": "" if record['x_studio_do_number'] == False else record['x_studio_do_number'],
                    
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
                    
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }
        
        r = requests.post(apiurl, data=json.dumps(payload), headers=headers)