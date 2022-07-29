# -*- coding: utf-8 -*-
# from odoo import http


# class ApiVen(http.Controller):
#     @http.route('/api_ven/api_ven', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/api_ven/api_ven/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('api_ven.listing', {
#             'root': '/api_ven/api_ven',
#             'objects': http.request.env['api_ven.api_ven'].search([]),
#         })

#     @http.route('/api_ven/api_ven/objects/<model("api_ven.api_ven"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('api_ven.object', {
#             'object': obj
#         })

import json, datetime, base64
from odoo import http
from odoo.http import request, Response
from datetime import datetime

def getRecord(self, model, field, wms):
        record = request.env[model].search([(field,'=',wms)])
        if record[field] == wms:
            return record['id']
        else:
            return -1
        
# @http.route('/api/authenticate', type='json', auth='none', methods=['POST'])
#     def authenticate(self, db, login, password):
#         try:
#             request.session.authenticate(db, login, password)
#             return request.env['ir.http'].session_info()
#         except:
#            Response.status = "401"
#             return {"Error": "Failed to authenticate user"}

@http.route('/api/createasn', type='json', auth='user', methods=['POST'])
    def post_rcpt(self, rcpt):
        created = 0
        error = {}
        warn_cnt = 1
        rcpt_lines = []
        is_error = False
        response_msg = "Failed to create GRN!"
        message = {}
        line_details = []
        is_partial = False
        
#         try:
#             api_log = request.env['api_ven.api_ven'].create({
#                 'status': 'new',
#                 'created_date': datetime.now(),
#                 'incoming_msg': ap,
#                 'message_type': 'ap'
#             })
#             api_log['status'] = 'process'
#         except:
#             error['Error'] = str(e)
#             is_error = True
            
#         try:
#             api_log['incoming_txt'] = request.env['ir.attachment'].create({
#                 'name': str(api_log['name']) + '_in.txt',
#                 'type': 'binary',
#                 'datas': base64.b64encode(bytes(str(ap), 'utf-8')),
#                 'res_model': 'api_ven.api_ven',
#                 'res_id': api_log['id'],
#                 'mimetype': 'text/plain'
#             })
#         except Exception as e:
#             error['Error'] = str(e)
#             is_error = True
        
       try:
        for rec in rcpt:
            #check poNo
            if rec['poNo'] == "":
                error["Error"] = "Field ownerReference is blank"
                is_error = True
                break

            po = self.getRecord(model="purchase.order", field="name", wms=rec['poNo'])
            if po == -1:
                error["Error"] = "poNo does not exist"
                is_error = True
                break

            #check receipt header
            receipt_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec['poNo']), ('picking_type_id', '=', 1), ('state', '=', 'assigned')])
            if receipt_header['origin'] != rec['poNo']:
                error["Error"] = "Receipt does not exist"
                is_error = True
                break

            #DocumentTransCode
            if rec['documentTransCode'] == "":
                error["Error"] = "Field documentTransCode is blank"
                is_error = True
                break

            #receiptDate
            if rec["receiptDate"] == "":
                receipt_date = ""
            else:
                try:
                    receipt_date = datetime.strptime(rec["receiptDate"], '%d/%m/%Y').date()
                except ValueError:
                    error["Error"] = "Wrong date format on receiptDate"
                    is_error = True
                    break


            response_msg = "GRN updated successfully"
            
        except Exception as e:
           error["Error"] = str(e)
           is_error = True

        if is_error == True:
#            Response.status = "400"
            pass
        else:
            Response.status = "200"
        
        message = {
            'response': response_msg, 
            'message': error
        }
        
        return message