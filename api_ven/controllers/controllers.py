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

@http.route('/api_sbt_inv/api_sbt_inv/', auth='public')
def getRecord(self, model, field, wms):
        record = request.env[model].search([(field,'=',wms)])
        if record[field] == wms:
            return record['id']
        else:
            return -1
        
@http.route('/api/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, db, login, password):
        try:
            request.session.authenticate(db, login, password)
            return request.env['ir.http'].session_info()
        except:
           Response.status = "401"
            return {"Error": "Failed to authenticate user"}

