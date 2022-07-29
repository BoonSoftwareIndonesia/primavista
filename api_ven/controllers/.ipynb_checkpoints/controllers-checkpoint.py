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

@http.route('/api_sbt_inv/api_sbt_inv/', auth='user')
def getRecord(self, model, field, wms):
        record = request.env[model].search([(field,'=',wms)])
        if record[field] == wms:
            return record['id']
        else:
            return -1


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
        
        try:
            for rec in rcpt:
                if rec['poNo'] == "":
                    error["Error"] = "Field ownerReference is blank"
                    is_error = True
                break

                po = self.getRecord(model="purchase.order", field="name", wms=rec['poNo'])
                if po == -1:
                    error["Error"] = "poNo does not exist"
                    is_error = True
                break
        except Exception as e:
            error["Error"] = str(e)
            is_error = True
            
        return is_error