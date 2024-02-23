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

class stockCompareApiController(models.Model):
    _inherit = ['odoo_wms_stock_compare.odoo_wms_stock_compare']

    def get_odoo_wms_compare(self):

        owner_code = ""
        #Checking the existing company first:
        if self.env.context['allowed_company_ids'][0] == 1: 
            owner_code = "PRIMAVISTA"
        else:
            owner_code = "AVO"
        
        # # The endpoint in WMS
        # apiurl = ""

        # # The header of the API request
        # headers = {
        #     "Content-Type": "application/json",
        #     "Connection": "keep-alive",
        #     "Accept": "*/*"
        # }

        # payload = {
        #     "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJpZCIsImlhdCI6MTYxMTYzNzI3NCwic3ViIjoiaWQiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0IiwiYXVkIjoib2N0cyIsImV4cCI6MTYxMTcyMzY3NH0.bB2S1bNFxf_D0s8Fp2BGTXNc9CRNjEiRqyWFBNDzZ4c",
        #     "ownerCode": owner_code,
        # }

        # # Create API log
        # try:
        #     api_log = request.env['api_ven.api_ven'].create({
        #         'status': 'new',
        #         'created_date': datetime.now(),
        #         'incoming_msg': payload,
        #         'message_type': 'GET_STOCK_COMP'
        #     })

        #     api_log['status'] = 'process'
        # except Exception as e:
        #     error['Error'] = str(e)
        #     is_error = True


        # # Create incoming txt
        # try:
        #     api_log['incoming_txt'] = request.env['ir.attachment'].create({
        #         'name': str(api_log['name']) + '_in.txt',
        #         'type': 'binary',
        #         'datas': base64.b64encode(bytes(str(payload), 'utf-8')),
        #         'res_model': 'api_ven.api_ven',
        #         'res_id': api_log['id'],
        #         'company_id': self.env.context['allowed_company_ids'][0],
        #         'mimetype': 'text/plain'
        #     })
        # except Exception as e:
        #     error['Error'] = str(e)
        #     is_error = True


        # # Post API request
        # resp = requests.post(apiurl, data=json.dumps(payload), headers=headers)

        # api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))
        # api_log['response_date'] = datetime.now()
        
        # if r.status_code == 200:
        #     api_log['status'] = 'success'
        # else:
        #     api_log['status'] = 'error'
        
        # # Create response txt
        # api_log['response_txt'] = request.env['ir.attachment'].create({
        #     'name': str(api_log['name']) + '_out.txt',
        #     'type': 'binary',
        #     'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
        #     'res_model': 'api_ven.api_ven',
        #     'res_id': api_log['id'],
        #     'company_id': self.env.context['allowed_company_ids'][0],
        #     'mimetype': 'text/plain'
        # })

        # # Changing the WMS response the list in python
        # ret = json.loads(resp.text)
        
        # return ret['stock_list']


    # def api_sap_dw_po(self):

    #     stock_list = self.get_odoo_wms_compare()

    #     raise UserError(f"Stock List")
            