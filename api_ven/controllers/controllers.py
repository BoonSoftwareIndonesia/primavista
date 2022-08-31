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

# ngetest override stock move create
# class PurchaseOrderLineExt(models.Model):
#     _inherit = 'purchase.order.line'
#     x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')
    
# #     @api.multi
#     def _prepare_stock_moves(self, picking):
#         res = super(PurchaseOrderLineExt, self)._prepare_stock_moves(picking)
#         for rec in res:
#             rec['x_studio_opt_char_1'] = self.x_studio_opt_char_1
#         return res

# class StockRuleExt(models.Model):
#     _inherit = 'stock.rule'
    
#     @api.model
#     def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
#         res = super(StockRuleExt, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
#         res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
#         return res
    
#     _inherit = 'stock.move'
#     x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')
# end test

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

    @http.route('/web/session/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, db, login, password, base_location=None):
            try:
                request.session.authenticate(db, login, password)
                return request.env['ir.http'].session_info()
            except:
    #            Response.status = "401"
                return {"Error": "Failed to authenticate user"}


    @http.route('/web/api/create_rcpt', type='json', auth='user', methods=['POST'])
    def post_rcpt(self, rcpt):
#             flag = 0
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

#             new_rcpt = json.dumps(rcpt)
            try:
                for rec in rcpt:
                    if rec['receiptNo'] == "":
                        error["Error"] = "Field ownerReference is blank"
                        is_error = True
                        break
                    
#                     return rec['receiptNo']
                    
                    po = self.getRecord(model="purchase.order", field="name", wms=rec['receiptNo'])
                    if po == -1:
                        error["Error"] = "receiptNo does not exist"
                        is_error = True
                        break

                    receipt_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec['receiptNo']), ('picking_type_id', '=', 1), ('state', '=', 'assigned')])
                    
                    
#               ini kudu di fixx di uncommand 
                    if receipt_header['origin'] != rec['receiptNo']:
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
                    
#                     flag = 0
                    #Receipt Line
                    for line in rec['details']:
                        line_details = []
#                         return line['quantityReceived']
                        
                        temp_product = 0

                        #ownerReference
#                         if line['ownerReference'] == "":
#                             error["Error"] = "Field ownerReference is blank"
#                             is_error = True
#                             break

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
#                                 "use_expiration_date": 1,
                                "company_id": 1
                            })

                            temp_product = created_product['id']

                            warn_str = "Message " + str(warn_cnt)
                            error[warn_str] = "Product " + line['product'] + " has been created"
                            warn_cnt += 1


                        #Check quantityReceived ================
                        if line['quantityReceived'] == "":
                            error["Error"] = "Field quantityReceived is blank"
                            is_error = True
                            break

                        #Check expiryDate
#                         if det['expiryDate'] == "":
#                             expiry_date = ""
#                         else:
#                             try:
#                                 expiry_date = datetime.strptime(det['expiryDate'], '%d/%m/%Y').date()
#                             except ValueError:
#                                 error["Error"] = "Wrong date format on expiryDate"
#                                 is_error = True
#                                 break

                        #Check stockStatusCode ===================
                        if line['stockStatusCode'] == "":
                            error["Error"] = "Field stockStatusCode is blank"
                            is_error = True
                            break

                        #Check lotNo
#                         if det['lotNo'] == "":
#                             error["Error"] = "Field lotNo is blank"
#                             is_error = True
#                             break
                        
#                         test
#                         quant = request.env['stock.quant'].search([("product_id", '=', temp_product)])
#                         hehe = request.env['stock.production.lot'].search([("id", '=', quant['lot_id'])])
#                         return quant['lot_id']
#                         test = request.env['stock.production.lot'].search([("id", '=', quant['lot_id']['id'])])
#                         return test['display_name']
#                         test


#                         temp_lot = request.env['stock.production.lot'].search([("name", '=', "21JR557")])
#                         return temp_lot['product_id']
#                         temp_lot = request.env["stock.production.lot"].search(['&',("product_id",'=',temp_product),("name", '=', line['lotNo'])])
#                         if temp_lot['name'] != line['lotNo']:
#                             temp_lot = request.env['stock.production.lot'].create({
#                                 "product_id": temp_product,
#                                 "name": line["lotNo"],
#                                 "company_id": 1
#                             })
#                         return temp_lot['id']

                            #Create Line Detail
#                             line_detail = request.env['stock.move.line'].create({
#                                 "product_id": temp_product,
#                                 "product_uom_id": 1,
#                                 "location_id": 4,
#                                 "location_dest_id": 8,
#                                 "lot_id": temp_lot['id'],
#                                 "expiration_date": expiry_date,
#                                 "qty_done": det["quantityReceived"],
#                                 "company_id": 1,
#                                 "state": "done"
#                             })

                        line_detail = request.env['stock.move.line'].create({
                            "product_id": temp_product,
                            "product_uom_id": 1,
                            "location_id": 4,
                            "location_dest_id": 8,
#                             "lot_id": "",
#                             "expiration_date": ,
#                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityReceived"],
                            "company_id": 1,
                            "state": "done"
                        })

                        line_details.append(line_detail['id'])

                        #Get existing receipt line data based on poNo and lineOptChar1
#                         receipt_line = request.env['stock.move'].search([('origin','=', rec['receiptNo']), ('product_id', '=', line['product'])])
                
                        receipt_line = request.env['stock.move'].search([('origin','=',rec['receiptNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"])])

#                         receipt_header.action_confirm()
#                         receipt_line._action_assign()
                        
                        if receipt_line['origin'] != rec['receiptNo']:
                            error["Error"] = "Stock Move not found"
                            is_error = True
                            break
                        
#                         
                    
                        #Get previous receipt line detail data
                        existing_detail = []
                        for i in receipt_line['move_line_nosuggest_ids']:
                            existing_detail.append(i['id'])
                        
#                         if existing_detail:
#                             line_details += existing_detail
                        
                    
                        #Merge new line details from JSON and existing line details
                        line_details += existing_detail

                        #Update line details data
                        receipt_line['move_line_nosuggest_ids'] = line_details
                        
                        #Check partial receipt (YANG BUAT RCPTNYA LGSG JD DONE) ==========================================
#                         if receipt_line['product_uom_qty'] == receipt_line['quantity_done']:
#                             receipt_line['state'] = 'assigned'
#                         else:
#                             is_partial = True


#                         TEST =====================
                    if is_error == True:
                        break

                    receipt_header['date_done'] = receipt_date
                    receipt_header['x_studio_document_trans_code'] = rec["documentTransCode"]

#                     if is_partial == False:
# #                         receipt_header.action_confirm()
# #                         receipt_header.button_validate()
#                         receipt_header['state'] = 'assigned'

                    response_msg = "GRN updated successfully"
#                         TEST ================
                        
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



#DW-DO
    @http.route('/web/api/downloaddo', type='json', auth='user', methods=['POST'])
    def post_do(self, do):
        created = 0
        error = {}
        warn_cnt = 1
        rcpt_lines = []
        is_error = False
        response_msg = "Failed to create DO!"
        message = {}
        line_details = []
        is_partial = False
        
        try:
            api_log = request.env['api_ven.api_ven'].create({
                 'status': 'new',
                 'created_date': datetime.now(),
                 'incoming_msg': do,
                 'message_type': 'DO'
               })
            api_log['status'] = 'process'
        except:
            error['Error'] = str(e)
            is_error = True
            
        try:
            api_log['incoming_txt'] = request.env['ir.attachment'].create({
                'name': str(api_log['name']) + '_in.txt',
                'type': 'binary',
                'datas': base64.b64encode(bytes(str(do), 'utf-8')),
                'res_model': 'api_ven.api_ven',
                'res_id': api_log['id'],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
            
#        try:
        for rec in do:
            #check soNo
            if rec['doNo'] == "":
                error["Error"] = "Field doNo is blank"
                is_error = True
                break

            sos = self.getRecord(model="sale.order", field="name", wms=rec['doNo'])
            if sos == -1:
                error["Error"] = "doNo does not exist"
                is_error = True
                break

            #check do header
            do_header = request.env["stock.picking"].search(['&','&', ('origin', '=', rec['doNo']), ('picking_type_id', '=', 2), ('state', '=', 'confirmed')])
#                 uncommand
            if do_header['origin'] != rec['doNo']:
                error["Error"] = "DO not found"
                is_error = True
                break

                #DispatchDate
            if rec["dispatchDate"] == "":
                dispatch_date = ""
            else:
                try:
                    dispatch_date = datetime.strptime(rec["dispatchDate"], '%d/%m/%Y').date()
                except ValueError:
                    error["Error"] = "Wrong date format on dispatchDate"
                    is_error = True
                    break
                
            #DocumentTransCode
            if rec['documentTransCode'] == "":
                error["Error"] = "Field documentTransCode is blank"
                is_error = True
                break

            #do Line
            for line in rec['details']:
                temp_product = 0

                #customerPO (DIISI APA DI POSTMAN?)
#                 if line['customerPO'] == "":
#                     error["Error"] = "Field customerPO is blank"
#                     is_error = True
#                     break

                #product
                if line['product'] == "":
                    error["Error"] = "Field product is blank"
                    is_error = True
                    break
                    
                 #soLineOptChar1
                if line['soLineOptChar1'] == "":
                    error["Error"] = "Field soLineOptChar1 is blank"
                    is_error = True
                    break   
                    
                #create product on the fly if product does not exist
                temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                if temp_product == -1:

                    created_product = request.env['product.product'].create({
                        "type": "product",
                        "default_code": line['product'],
                        "name": line['product'],
                        "tracking": "lot",
#                         "use_expiration_date": 1,
                        "company_id": 1
                    })

                    temp_product = created_product['id']

                    warn_str = "Message " + str(warn_cnt)
                    error[warn_str] = "Product " + line['product'] + " has been created"
                    warn_cnt += 1
# uncommand
#                 for det in line['lineDetails']:

                    #Check quantityShipped
                if line['quantityShipped'] == "":
                    error["Error"] = "Field quantityShipped is blank"
                    is_error = True
                    break

#                     #Check expiryDate
#                     if det['expiryDate'] == "":
#                         expiry_date = ""
#                     else:
#                         try:
#                             expiry_date = datetime.strptime(det['expiryDate'], '%d/%m/%Y').date()
#                         except ValueError:
#                             error["Error"] = "Wrong date format on expiryDate"
#                             is_error = True
#                             break
                            
#                     #Check lotNo
#                     if det['lotNo'] == "":
#                         error["Error"] = "Field lotNo is blank"
#                         is_error = True
#                         break

                    #Check stockStatusCode
                if line['stockStatusCode'] == "":
                    error["Error"] = "Field stockStatusCode is blank"
                    is_error = True
                    break

#                     temp_lot = request.env["stock.production.lot"].search(['&',("product_id",'=',temp_product),("name", '=', det['lotNo'])])
#                     if temp_lot['name'] != det['lotNo']:
#                         error["Error"] = "lot number does not exist!"
#                         is_error = True
#                         break
# sampe sini
                    #Create Line Detail
#                     line_detail = request.env['stock.move.line'].create({
#                         "product_id": temp_product,
#                         "product_uom_id": 1,
#                         "location_id": 8,
#                         "location_dest_id": 5,
#                         "lot_id": temp_lot['id'],
#                         "expiration_date": expiry_date,
#                         "qty_done": det["quantityShipped"],
#                         "company_id": 1,
#                         "state": "done"
#                     })
                line_detail = request.env['stock.move.line'].create({
                    "product_id": temp_product,
                    "product_uom_id": 1,
                    "location_id": 1,
                    "location_dest_id": 1,
#                         "lot_id": temp_lot['id'], nanti unccommand
#                         "lot_id": 1,
#                         "expiration_date": expiry_date,
                    "qty_done": line["quantityShipped"],
                    "company_id": 1,
                    "state": "done"
                })

                line_details.append(line_detail['id'])

                #Get existing dispatch line data based on doNo and lineOptChar1
                dispatch_line = request.env['stock.move'].search(['&',('origin','=',rec['doNo']),('x_studio_opt_char_1', '=', line["soLineOptChar1"])])
                
#                 uncommand (KYKNY BUKAN SOREFERENCE TP DONO)
#                 if dispatch_line['origin'] != rec['soReference']:
#                     error["Error"] = "Stock Move not found"
#                     is_error = True
#                     break
    
                if dispatch_line['origin'] != rec['doNo']:
                    error["Error"] = "Stock Move not found"
                    is_error = True
                    break
    
                #Get previous dispatch line detail data
                existing_detail = []
                for i in dispatch_line['move_line_ids']:
                    existing_detail.append(i['id'])
                    
                #Merge new line details from JSON and existing line details
                line_details += existing_detail
                
                #Update line details data
                dispatch_line['move_line_ids'] = line_details
                
                #Check partial receipt
                if dispatch_line['product_uom_qty'] == dispatch_line['quantity_done']:
                    dispatch_line['state'] = 'done'
                else:
                    is_partial = True


                if is_error == True:
                    break

            if is_error == True:
                break
            
            do_header['x_studio_dispatch_date'] = dispatch_date
            do_header['x_studio_document_trans_code'] = rec["documentTransCode"]
            
            if is_partial == False:
                do_header['state'] = 'done'

            response_msg = "DO updated successfully"
#        except Exception as e:
#            error["Error"] = str(e)
#            is_error = True

        if is_error == True:
#            Response.status = "400"
            pass
        else:
            Response.status = "200"
        
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
        
        return message