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


class SAPApiController(models.Model):
    _inherit = ['purchase.order']
    
    def api_sap_dw_po(self, record):
            
        # The endpoint in SAP
        apiurl = "https://cloud1.boonsoftware.com/trn_avi_api/getlotlist"

        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"

        # A variable to store the value of the current line number
        line_no = 1
        # An array to store the PO lines
        po_lines = []
        # To store the origin of this PO (the SO(s) that generated this PO)
        res = ""
        unique_res = ""
        owner_code = ""

        # To get the SO No that generated this PO
        # If this PO is generated from another SO, we also need to send the list of SO that generated this PO
        # Use regex to get the SO no only
        # Example: OP/00272 - SO/POV/2022/11/24/00178 -> SO/POV/2022/11/24/00178
        # re.findall() is used to return all non-overlapping matches of pattern in string, as a list of strings
        # The string is scanned left-to-right, and matches are returned in the order found.
        if record['origin']:
            res = re.findall(r'S[\w\/]*', record['origin'])
            unique_res = str(set(res))
            
        # ==============================================
        # Loop through all purchase order lines
        for line in record['order_line']:
            # If there is a PO line whose default code is empty, continue, don't send to WMS
            if line['product_id']["product_tmpl_id"]["default_code"] is False:
                continue

            # Set the current line's x_studio_line_opt_char_1 as the value of the current line_no
            line['x_studio_opt_char_1'] = str(line_no)

            # Create po line (Refer to the mapping documentation)
            po_line = {
                "ItemCode": line['product_id']["product_tmpl_id"]["default_code"].upper(),
                "Quantity": str(line['product_qty']),
                "Price": str(line['price_subtotal']),
                "DiscountPercent": "0" if line['x_regular_discount'] == False else line['x_regular_discount'],
                "MeasureUnit": "UNITS" if line['product_uom']['name'] == False else line['product_uom']['name'].upper(),
                "WarehouseCode": "HARDCODE_WH"
            }

            # Increment the line_no
            line_no += 1
            # Append the current po_line to the po_lines array
            po_lines.append(po_line)
        # ==============================================

        raw_date_approval = record['date_approve']
        date_approval = raw_date_approval.strftime("%Y/%m/%d")
        raw_date_planned = record['date_planned']
        date_planned = raw_date_planned.strftime("%Y/%m/%d")
        
        # Create payload (Refer to the mapping documentation). These are the data that will be sent from Odoo to WMS
        # The access token for the WMS needs to be changed to prd's access token if we want to patch to prd
        payload = {
            "DocDate": date_approval,
            "DocDueDate": date_planned,
            "CardCode": "" if record['partner_id']['x_studio_customer_id'] == False else record['partner_id']['x_studio_customer_id'],
            "NumAtCard": "",
            "Comments": "" if record['notes'] == False else record['notes'],
            "TransType": "OMRON" if record['x_studio_doc_trans_code'] == False else record['x_studio_doc_trans_code'].upper(),
            "OwnerCode": owner_code,
            "Collector": "",
            "SalesPrincipal": "",
            "ChanOrd": "",
            "TransactionTime": date_approval,
            "Shipto": "",
            "DocumentLines": po_lines
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