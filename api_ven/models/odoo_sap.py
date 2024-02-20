from odoo import models, fields, api
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
    - This is models that handle external (SAP) API

    SAP API:
    1. api_sap_dw_po => API that send when Odoo create PO. (This will be converted into SO in SAP)
"""

class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'
    x_collector = fields.Selection([("ECO", "ECO"), ("NA", "NA"),],string="Collector", default='NA')
    x_sales_principal = fields.Selection([("3M", "3M"), ("ACUVUE", "ACUVUE"),  ("AKMU", "AKMU"), ("ALPHA", "ALPHA"), ("APA", "APA"), ("BAUSCH LOMB IND", "BAUSCH LOMB IND"), ("BERNOFARM OTC", "BERNOFARM OTC"), ("DKT", "DKT"), ("ESSILOR 2.5 NVG", "ESSILOR 2.5 NVG"), ("ESSILOR NVG CONS", "ESSILOR NVG CONS"), ("FRESH EYE", "FRESH EYE"), ("GALENIUM PSC", "GALENIUM PSC"), ("GEO MEDICAL", "GEO MEDICAL"), ("JENNY HOUSE", "JENNY HOUSE"), ("KINO MEDICAL", "KINO MEDICAL"), ("KLARENS", "KLARENS"), ("MEIJI IND ETC", "MEIJI IND ETC"), ("MPS", "MPS"), ("OMRON", "OMRON"), ("ONEMED", "ONEMED"), ("SENSI", "SENSI"), ("TAKEDA OTC", "TAKEDA OTC"), ("THERASKIN", "THERASKIN"), ("VITAHEALTH CONS", "VITAHEALTH CONS"), ("NA", "NA")],string="Sales Principal", default='NA')
    x_chanord = fields.Selection([("ECO", "ECO"), ("NA", "NA"),],string="Chanord", default='NA')

class SAPApiController(models.Model):
    _inherit = ['purchase.order']

    # Odoo (Request Access Token)
    def api_sap_get_access_token(self):

        # The endpoint in SAP
        apiurl = "http://b1webconnect.beonesolution.com:2106/GetToken"
        
        # The header of the API request
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }
    
        payload = {
            "username" : "Beone123",
            "password" : "Be0ne$123"
        }

        # Post the API request 
        resp = requests.post(apiurl, headers=headers, data=json.dumps(payload))

        # Changing the WMS response the list in python
        ret = json.loads(resp.text)
        
        return ret['accesstoken']

    # Odoo (Purchase Order) to SAP (Sales Order)
    def api_sap_dw_po(self, record):

        SAP_access_Token = self.api_sap_get_access_token()
            
        # The endpoint in SAP
        apiurl = "http://b1webconnect.beonesolution.com:2106/Orders"

        # An array to store the PO lines
        po_lines = []
        
        owner_code = ""
        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
            
        # ==============================================
        # Loop through all purchase order lines
        for line in record['order_line']:
            # If there is a PO line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue

            # Create po line (Refer to the mapping documentation)
            po_line = {
                "ItemCode": line['product_id']["product_tmpl_id"]["default_code"].upper(),
                "Quantity": line['product_qty'],
                "Price": line['price_unit'],
                "DiscountPercent": 0 if line['x_regular_discount'] == False else line['x_regular_discount'],
                "MeasureUnit": "PCS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
                "WarehouseCode": "HARDCODE_WH"
            }

            # Append the current po_line to the po_lines array
            po_lines.append(po_line)
        # ==============================================

        raw_date_approval = record['date_approve']
        date_approval = raw_date_approval.strftime("%Y/%m/%d")
        raw_date_planned = record['date_planned']
        date_planned = raw_date_planned.strftime("%Y/%m/%d")

        date_approval_time = raw_date_approval.time()
        
        # Create payload (Refer to the mapping documentation). These are the data that will be sent from Odoo to WMS
        # The access token for the WMS needs to be changed to prd's access token if we want to patch to prd
        # Card code akan menjadi jadi hardcode code dari AVO
        # Owner Code akan menjadi customer_id
        payload = {
            "DocDate": date_approval,
            "DocDueDate": date_planned,
            "CardCode": "" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
            "NumAtCard": "" if record['name'] == False else record['name'],
            "Comments": "" if record['notes'] == False else record['notes'],
            "TransType": "OMRON" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'].upper(),
            "OwnerCode": owner_code,
            "Collector": "" if record['x_collector'] == False else record['x_collector'],
            "SalesPrincipal": "" if record['x_sales_principal'] == False else record['x_sales_principal'],
            "ChanOrd": "" if record['x_chanord'] == False else record['x_chanord'],
            "TransactionTime": str(date_approval_time),
            "Shipto": "Jakarta" if record['company_id']['city'] == False else record['company_id']['city'],
            "DocumentLines": po_lines
        }

        # The header of the API request
        headers = {
            "HTTP-KEY": SAP_access_Token,
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
                'message_type': 'SAP_PO'
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

        # Create response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })

        if resp.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'