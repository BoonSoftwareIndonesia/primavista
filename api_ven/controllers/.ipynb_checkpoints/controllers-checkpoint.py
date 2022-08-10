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

from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
from datetime import datetime
from odoo import http

# import json, datetime, base64
# from odoo import http
# from odoo.http import request, Response
# from datetime import datetime

class ApiVen(http.Controller):
    # @http.route('/api_sbt_inv/api_sbt_inv/', auth='user')
    def getRecord(self, model, field, wms):
            record = request.env[model].search([(field,'=',wms)])
            if record[field] == wms:
                return record['id']
            else:
                return -1

    @http.route('/hello/hello/', auth='user')
    def index(self, **kw):
            return "Hello, world"

    @http.route('/web/api/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, db, login, password):
            try:
                request.session.authenticate(db, login, password)
                return request.env['ir.http'].session_info()
            except:
    #            Response.status = "401"
                return {"Error": "Failed to authenticate user"}


    @http.route('/web/api/create_rcpt', type='json', auth='user', methods=['POST'])
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

            #Create log
            try:
                api_log = request.env['api_ven.api_ven'].create({
                    'status': 'new',
                    'created_date': datetime.now(),
                    'incoming_msg': rcpt,
                    'message_type': 'RCPT'
                })

                api_log['status'] = 'process'
            except:
                error['Error'] = str(e)
                is_error = True

            try:
                api_log['incoming_txt'] = request.env['ir.attachment'].create({
                    'name': str(api_log['name']) + '_in.txt',
                    'type': 'binary',
                    'datas': base64.b64encode(bytes(str(rcpt), 'utf-8')),
                    'res_model': 'api_ven.api_ven',
                    'res_id': api_log['id'],
                    'mimetype': 'text/plain'
                })
            except Exception as e:
                error['Error'] = str(e)
                is_error = True

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

                    #Receipt Line
                    for line in rec['details']:
                        temp_product = 0

                        #ownerReference
                        if line['ownerReference'] == "":
                            error["Error"] = "Field ownerReference is blank"
                            is_error = True
                            break

                        #inwardLineOptChar1
                        if line['inwardLineOptChar1'] == "":
                            error["Error"] = "Field inwardLineOptChar1 is blank"
                            is_error = True
                            break

                        #product
                        if line['product'] == "":
                            error["Error"] = "Field product is blank"
                            is_error = True
                            break

                        temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                        if temp_product == -1:

                            created_product = request.env['product.product'].create({
                                "type": "product",
                                "default_code": line['product'],
                                "name": line['product'],
                                "tracking": "lot",
                                "use_expiration_date": 1,
                                "company_id": 1
                            })

                            temp_product = created_product['id']

                            warn_str = "Message " + str(warn_cnt)
                            error[warn_str] = "Product " + line['product'] + " has been created"
                            warn_cnt += 1

                        for det in line['lineDetails']:

                            #Check quantityReceived
                            if det['quantityReceived'] == "":
                                error["Error"] = "Field quantityReceived is blank"
                                is_error = True
                                break

                            #Check expiryDate
                            if det['expiryDate'] == "":
                                expiry_date = ""
                            else:
                                try:
                                    expiry_date = datetime.strptime(det['expiryDate'], '%d/%m/%Y').date()
                                except ValueError:
                                    error["Error"] = "Wrong date format on expiryDate"
                                    is_error = True
                                    break

                            #Check stockStatusCode
                            if det['stockStatusCode'] == "":
                                error["Error"] = "Field stockStatusCode is blank"
                                is_error = True
                                break

                            #Check lotNo
                            if det['lotNo'] == "":
                                error["Error"] = "Field lotNo is blank"
                                is_error = True
                                break

                            temp_lot = request.env["stock.production.lot"].search(['&',("product_id",'=',temp_product),("name", '=', det['lotNo'])])
                            if temp_lot['name'] != det['lotNo']:
                                temp_lot = request.env['stock.production.lot'].create({
                                    "product_id": temp_product,
                                    "name": det["lotNo"],
                                    "company_id": 1
                                })

                            #Create Line Detail
                            line_detail = request.env['stock.move.line'].create({
                                "product_id": temp_product,
                                "product_uom_id": 1,
                                "location_id": 4,
                                "location_dest_id": 8,
                                "lot_id": temp_lot['id'],
                                "expiration_date": expiry_date,
                                "qty_done": det["quantityReceived"],
                                "company_id": 1,
                                "state": "done"
                            })

                            line_details.append(line_detail['id'])

                        #Get existing receipt line data based on poNo and lineOptChar1
                        receipt_line = request.env['stock.move'].search(['&',('origin','=',rec['poNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"])])
                        if receipt_line['origin'] != rec['poNo']:
                            error["Error"] = "Stock Move not found"
                            is_error = True
                            break

                        #Get previous receipt line detail data
                        existing_detail = []
                        for i in receipt_line['move_line_nosuggest_ids']:
                            existing_detail.append(i['id'])

                        #Merge new line details from JSON and existing line details
                        line_details += existing_detail

                        #Update line details data
                        receipt_line['move_line_nosuggest_ids'] = line_details

                        #Check partial receipt
                        if receipt_line['product_uom_qty'] == receipt_line['quantity_done']:
                            receipt_line['state'] = 'done'
                        else:
                            is_partial = True


                        if is_error == True:
                            break

                        receipt_header['date_done'] = receipt_date
                        receipt_header['x_studio_document_trans_code'] = rec["documentTransCode"]

                        if is_partial == False:
                            receipt_header['state'] = 'done'

                        response_msg = "GRN updated successfully"
                        
                except Exception as e:
                    error["Error"] = str(e)
                    is_error = True
                    
# ini dipindahin kebawah
                if is_error == True:
    #            Response.status = "400"
                    api_log['status'] = 'error'
#                     pass
                else:
                    Response.status = "200"
                    api_log['status'] = 'success'
                
#                 ini di uncommmnd
                message = {
                    'response': response_msg, 
                    'message': error
                } 
            
                api_log['response_msg'] = message
                api_log['response_date'] = datetime.now()

                api_log['response_txt'] = request.env['ir.attachment'].create({
                    'name': str(api_log['name']) + '_out.txt',
                    'type': 'binary',
                    'datas': base64.b64encode(bytes(str(message), 'utf-8')),
                    'res_model': 'api_ven.api_ven',
                    'res_id': api_log['id'],
                    'mimetype': 'text/plain'
                })
# sampe sini


#             except Exception as e:
#                 error["Error"] = str(e)
#                 is_error = True

                return message