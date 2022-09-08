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

    @http.route('/web/session/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, db, login, password, base_location=None):
            try:
                request.session.authenticate(db, login, password)
                return request.env['ir.http'].session_info()
            except:
    #            Response.status = "401"
                return {"Error": "Failed to authenticate user"}

    def validate_receipt_header(self, rec, error):
        receipt_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec['receiptNo']), ('picking_type_id', '=', 1), ('state', '=', 'assigned')])
#         Origin
#         return rec['receiptNo']
        if receipt_header['origin'] != rec['receiptNo']:
            error["Error"] = "Receipt does not exist"
            return -1

        #DocumentTransCode
        if rec['documentTransCode'] == "":
            error["Error"] = "Field documentTransCode is blank"
            return -1
        
        return receipt_header
    
    def validate_receipt_date(self, rec, error):
        if rec["receiptDate"] == "":
            return ""
        else:
            try:
                receipt_date = datetime.strptime(rec["receiptDate"], '%d/%m/%Y').date()
                return receipt_date
            except ValueError:
                error["Error"] = "Wrong date format on receiptDate"
                return -1
        
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

#             new_rcpt = json.dumps(rcpt)
            try:
                for rec in rcpt:
                    if rec['receiptNo'] == "":
                        error["Error"] = "Field ownerReference is blank"
                        is_error = True
                        break
                    
                    po = self.getRecord(model="purchase.order", field="name", wms=rec['receiptNo'])
                    if po == -1:
                        error["Error"] = "receiptNo does not exist"
                        is_error = True
                        break
                
#                   ReceiptHeader
                    receipt_header = self.validate_receipt_header(rec, error)
                    if receipt_header == -1:
                        is_error = True
                        break
                    
#                   ReceiptDate
                    receipt_date = self.validate_receipt_date(rec, error)
                    if receipt_date == -1:
                        is_error = True
                        break
                    
                    #Receipt Line
                    for line in rec['details']:
                        line_details = []
                        
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
                            
#                       Create a new product does not exist yet, else use existing product
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


#                         temp_lot = request.env["stock.production.lot"].search(['&',("product_id",'=',temp_product),("name", '=', line['lotNo'])])
#                         if temp_lot['name'] != line['lotNo']:
#                             temp_lot = request.env['stock.production.lot'].create({
#                                 "product_id": temp_product,
#                                 "name": line["lotNo"],
#                                 "company_id": 1
#                             })

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
                        

#                       Create a new move stock line when item is received
                        line_detail = request.env['stock.move.line'].create({
                            "product_id": temp_product,
                            "product_uom_id": 27,
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

                        #Get existing receipt line data based on poNo, lineOptChar1, and status
                        receipt_line = request.env['stock.move'].search(['&', '&', ('origin','=',rec['receiptNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"]), ('state', '=', 'assigned')])
                        
                        if receipt_line['origin'] != rec['receiptNo']:
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
                        
                        #Check if qty received is partial or not
                        if receipt_line['product_uom_qty'] == receipt_line['quantity_done']:
                            is_partial = False
                        else:
                            is_partial = True


#                         INDENT  =====================
                    
                    if is_error == True:
                        break
            
                    receipt_header['date_done'] = receipt_date
                    receipt_header['x_studio_document_trans_code'] = rec["documentTransCode"]

#                   Receipt Validate
                    self.validate_receipt(receipt_header, po, is_partial)
    
                    response_msg = "GRN updated successfully"
#                         INDENT ================
                        
            except Exception as e:
                error["Error"] = str(e)
                is_error = True
                    
#           ini dipindahin kebawah
            if is_error == True:
    #            Response.status = "400"
                api_log['status'] = 'error'
#                     pass
            else:
                Response.status = "200"
                api_log['status'] = 'success'
                
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


#             except Exception as e:
#                 error["Error"] = str(e)
#                 is_error = True

            return message

    def create_immediate_transfer(self, po_name):
            po_obj = request.env['purchase.order'].search([('name', '=', po_name )])

            immediate_transfer_line_ids = []

            for picking in po_obj.picking_ids:
                if picking['state'] == 'assigned':
                    immediate_transfer_line_ids.append([0, False, {
                            'picking_id': picking.id,
                            'to_immediate': True
                    }])

            res = request.env['stock.immediate.transfer'].create({
                'pick_ids': [(4, p.id) for p in po_obj.picking_ids],
                'show_transfers': False,
                'immediate_transfer_line_ids': immediate_transfer_line_ids
            })

            return res
    
    def validate_receipt(self, receipt_header, po, is_partial):
        if is_partial == False:
        # If there is no partial received items, then change the stock picking to stock.immediate(similar to pushing a button). When stock picking change to stock      immediate, it will be picked urgently and backorder cannot be created. So, each product has to fullfil the required qty. Then, the picking status will be changed to done.
#             po_name = 'P00' + str(int(po))
            po_name = receipt_header['origin']
#             po_name = 'P00216'
            res = self.create_immediate_transfer(po_name)
            receipt_header.with_context(cancel_backorder=True)._action_done()
    #       res.with_context(button_validate_picking_ids=res.pick_ids.ids).process()
        else:
        # If there is a partial order, we do not change it to stock.immediate as we want to create backorder. So, we get the stock.picking, and process while also create a backorder.
            receipt_header.with_context(cancel_backorder=False)._action_done()
        



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

#             return sos
                
            #check do header
            do_header = request.env["stock.picking"].search(['&','&', ('origin', '=', rec['doNo']), ('picking_type_id', '=', 2), ('state', '=', 'assigned')])
#             (STOCK PICKING NYA UDH DLM STATE READY (ASSIGNED) BUKAN WAITING (CONFIRMED))
#             do_header = request.env["stock.picking"].search(['&','&', ('origin', '=', rec['doNo']), ('picking_type_id', '=', 2), ('state', '=', 'confirmed')])
            
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
                line_details = []
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
    
#                 LOCATION ID AMA DEST ID SBLMNNYA SAMA2 1, product uom id nya tadinya 1
                line_detail = request.env['stock.move.line'].create({
                    "product_id": temp_product,
#                     "product_uom_id":  1,
                    "product_uom_id":  27,
                    "location_id": 8,
                    "location_dest_id": 5,
#                         "lot_id": temp_lot['id'], nanti unccommand
#                         "lot_id": 1,
#                         "expiration_date": expiry_date,
                    "qty_done": line["quantityShipped"],
                    "company_id": 1,
                    "state": "done"
                })

                line_details.append(line_detail['id'])

                #Get existing dispatch line data based on doNo and lineOptChar1
                dispatch_line = request.env['stock.move'].search(['&', '&',('origin','=',rec['doNo']),('x_studio_opt_char_1', '=', line["soLineOptChar1"]), ('state', '=', 'assigned')])
    
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
                    dispatch_line._quantity_done_compute()
                    is_partial = False
                else:
                    is_partial = True


                if is_error == True:
                    break

            if is_error == True:
                break
            
            do_header['x_studio_dispatch_date'] = dispatch_date
            do_header['x_studio_document_trans_code'] = rec["documentTransCode"]

#             Delivery Order Validate
            self.validate_delivery(do_header, sos, is_partial)
            
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
    
    def create_immediate_transfer_so(self, so_name):
        so_obj = request.env['sale.order'].search([('name', '=', so_name )])
        
        immediate_transfer_line_ids = []
        
        for picking in so_obj.picking_ids:
            if picking['state'] == 'assigned':
                immediate_transfer_line_ids.append([0, False, {
                    'picking_id': picking.id,
                    'to_immediate': True
                }])

        res = request.env['stock.immediate.transfer'].create({
            'pick_ids': [(4, p.id) for p in so_obj.picking_ids],
            'show_transfers': False,
            'immediate_transfer_line_ids': immediate_transfer_line_ids
        })

        return res
#         return res.with_context(button_validate_picking_ids=res.pick_ids.ids).process()

    def validate_delivery(self, do_header, sos, is_partial):
        if is_partial == False:
#             so_name = 'S000' + str(int(sos))
            so_name = do_header['origin']
            res = self.create_immediate_transfer_so(so_name)
            do_header.with_context(cancel_backorder=True)._action_done()
#             res.with_context(button_validate_picking_ids=res.pick_ids.ids).process()
        else:
            do_header.with_context(cancel_backorder=False)._action_done()
#             do_header._action_done()