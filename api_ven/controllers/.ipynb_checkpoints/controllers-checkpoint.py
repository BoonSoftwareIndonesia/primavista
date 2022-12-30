from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
from datetime import datetime
from odoo import http
from odoo.exceptions import UserError

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

    # API for authentication ===================================================================================
    @http.route('/web/session/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, db, login, password):
            try:
                request.session.authenticate(db, login, password)
                return request.env['ir.http'].session_info()
            except:
                # Response.status = "401"
                return {"Error": "Failed to authenticate user"}

    
    # Validations
    def validate_obj_header(self, rec, error, rec_no_type, pick_type_id):
        # obj_header validation
        try:
            obj_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec[rec_no_type]), ('picking_type_id', '=', pick_type_id), ('state', '=', 'assigned')])
        except Exception as e:
            error['Error'] = 'Error in searching stock.picking ' + str(e)
            return -1

        if obj_header['origin'] != rec[rec_no_type]:
            if rec_no_type == 'poNo':
                error["Error"] = "Receipt does not exist"
            else:
                error["Error"] = "Delivery order does not exist"
            return -1

        if rec_no_type == 'poNo':
            # PO
            # set WMS rec no of stock picking
            obj_header['x_wms_rec_no'] = rec['receiptNo']
        else:
            # SO
            # set WMS rec no of stock picking
            obj_header['x_wms_rec_no'] = rec['doNo']

        return obj_header

    def validate_obj_json(self, rec, error, rec_no_type):
        # rec validation
        if rec[rec_no_type] == "":
            error["Error"] = "Field " + rec_no_type + " is blank"  
            return -1
            
        if rec['documentTransCode'] == "":
            error["Error"] = "Field documentTransCode is blank"
            return -1
        
        # check x wms rec no
        if rec_no_type == 'poNo':
            if rec['receiptNo'] == "" or 'receiptNo' not in rec:
                error["Error"] = "Field WMS Receipt Number is blank"
                return -1
        else:
            if rec['doNo'] == "" or 'doNo' not in rec:
                error["Error"] = "Field WMS DO Number is blank"
                return -1
        
        return 1
    
    def validate_obj_date(self, rec, error, date_type):
        if rec[date_type] == "":
            return ""
        else:
            try:
                obj_date = datetime.strptime(rec[date_type], '%d/%m/%Y').date()
                return obj_date
            except ValueError:
                error["Error"] = "Wrong date format on " + date_type 
                return -1

    # Rollback previous stock move lines
    def rollback_move(self, rec, error, lines, rec_no_type):
        if lines:
            # if there are previous products
            # loop through the list, search for the stock move, unreserve the stock move
            for line in lines:
                curr_move = request.env['stock.move'].search(['&', '&', ('origin','=', rec[rec_no_type]),('x_studio_opt_char_1', '=', str(line)), ('state', '=', 'assigned')])
                
                curr_move.move_line_nosuggest_ids.write({'qty_done': 0})
    
    # CREATE RCPT (PO) API ===================================================================================
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
                    # x_studio_opt_char containers for searching stock move line to be reversed
                    lines = []
                    
                    po = self.getRecord(model="purchase.order", field="name", wms=rec['poNo'])
                    if po == -1:
                        error["Error"] = "receipt no does not exist"
                        is_error = True
                        break
                    
                    json_valid = self.validate_obj_json(rec, error, "poNo")
                    if json_valid == -1:
                        is_error = True
                        break
                    
                    # ReceiptHeader
                    receipt_header = self.validate_obj_header(rec, error, "poNo", 1)
                    if receipt_header == -1:
                        is_error = True
                        break
                    
                    # ReceiptDate
                    receipt_date = self.validate_obj_date(rec, error, "receiptDate")
                    if receipt_date == -1:
                        is_error = True
                        break
                    
                    #Receipt Line
                    for line in rec['details']:
                        line_details = []
                        
                        temp_product = 0

                        # LINE VALIDATION ==============================================================
                        #inwardLineOptChar1
                        if line['inwardLineOptChar1'] == "":
                            error["Error"] = "Field inwardLineOptChar1 is blank"
                            is_error = True
                            break
                        
                        # product
                        if line['product'] == "":
                            error["Error"] = "Field product is blank"
                            is_error = True
                            break
                            
                        # check status code
                        if line['stockStatusCode'] == "":
                            error["Error"] = "Field stockStatusCode is blank"
                            is_error = True
                            break
                    
                        # check quantityReceived
                        if line['quantityReceived'] == "":
                            error["Error"] = "Field quantityReceived is blank"
                            is_error = True
                            break
                        
                        try:
                            receipt_line = request.env['stock.move'].search(['&', '&', ('origin','=',rec['poNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"]), ('state', '=', 'assigned')])
                        except Exception as e:
                            error['Error'] = "Searching stock move error " +str(e)
                            is_error = True
                            break
                        
                        if receipt_line['origin'] != rec['poNo']:
                            error["Error"] = "Stock Move not found"
                            is_error = True
                            break
                        
                        # set WMS Rec No of stock move
                        receipt_line['x_wms_rec_no'] = rec['receiptNo']
                        
                        # LINE VALIDATION END ==============================================================
                            
                        # search existing product
                        try:
                            temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                        except Exception as e:
                            error["Error"] = "Error in searching existing product " + str(e)
                            is_error = True
                            break
                            
                        if temp_product == -1:
                            error["Error"] = "Product does not exist"
                            is_error = True
                            break

                        # check whether quantityReceived exceeds the demand
                        if receipt_line["product_uom_qty"] < int(line["quantityReceived"]):
                            error["Error"] = "Quantity received exceeds demand"
                            is_error = True
                            break

                        # create a new move stock line when item is received
                        receipt_line.move_line_ids.write({
                            "product_id": temp_product,
                            "product_uom_id": 26,
                            "location_id": 4,
                            "location_dest_id": 8,
#                             "lot_id": "",
#                             "expiration_date": ,
#                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityReceived"],
                            "company_id": 1,
#                             "state": "done",
                            "x_wms_rec_no": rec['receiptNo']
                        })
                        
                        lines.append(line["inwardLineOptChar1"])
        
                        # check if qty received is partial or not
                        if receipt_line['product_uom_qty'] > receipt_line['quantity_done']:
                            is_partial = True

                    # INDENT  =========================
                    if is_error == True:
                        self.rollback_move(rec, error, lines, "poNo")
                        break
            
                    receipt_header['date_done'] = receipt_date
                    receipt_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                    
                    
                    # if the number of details is less than the list of products in the stock picking
                    # then it is a partial case
                    moves = receipt_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                    if len(rec['details']) < len(moves):
                        is_partial = True
                    
                    # receipt Validate
                    self.validate_receipt(receipt_header, is_partial)
                    
                    response_msg = "GRN updated successfully"
                    # INDENT ===========================
                        
            except Exception as e:
                error["Error"] = str(e)
                is_error = True
                    
            if is_error == True:
                api_log['status'] = 'error'
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
    
    def validate_receipt(self, receipt_header, is_partial):
        if is_partial == False:
            # If there is no partial received items, then change the stock picking to stock.immediate(similar to pushing a button). 
            # When stock picking change to stock immediate, it will be picked urgently and backorder cannot be created. 
            # So, each product has to fullfil the required qty. Then, the picking status will be changed to done.

            po_name = receipt_header['origin']
            res = self.create_immediate_transfer(po_name)
            receipt_header.with_context(cancel_backorder=True)._action_done()
        else:
            # If there is a partial order, we do not change it to stock.immediate as we want to create backorder. 
            # So, we get the stock.picking, and process while also create a backorder.
            receipt_header.with_context(cancel_backorder=False)._action_done()

     # stock picking validation for returns (search based on wms rec no)
    def validate_return_obj_header(self, rec, error, pick_type_id, rec_no_type):
        # obj_header validation for po and so return api
        try:
            obj_header = request.env["stock.picking"].search(['&', ('x_wms_rec_no', '=', rec[rec_no_type]), ('state', '=', 'assigned')])
        except Exception as e:
            error["Error"] = 'Error in searching stock picking ' + str(e)
            return -1

        if obj_header['x_wms_rec_no'] != rec[rec_no_type]:
            if pick_type_id == 1 :
                error["Error"] = "Return receipt does not exist"
            else:
                error["Error"] = "Return delivery order does not exist"
            return -1

        return obj_header   
    
    # PO-RETURN ===================================================================================
    @http.route('/web/api/return_rcpt', type='json', auth='user', methods=['POST'])
    def return_rcpt(self, do):
        created = 0
        error = {}
        warn_cnt = 1
        rcpt_lines = []
        is_error = False
        response_msg = "Failed to create GRN!"
        message = {}
        line_details = []
        is_partial = False
        api_log = request.env['api_ven.api_ven']

        #Create log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': do,
                'message_type': 'RCPT_RET'
            })

            api_log['status'] = 'process'
        except Exception as e:
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
        
        try:
            for rec in do:
                lines = []
                json_valid = self.validate_obj_json(rec, error, "soNo")
                if json_valid == -1:
                    is_error = True
                    break
                    
                # ReceiptHeader
                # search the stock picking based on x wms rec no
                receipt_header = self.validate_return_obj_header(rec, error, 1, "receiptNo")
                if receipt_header == -1:
                    is_error = True
                    break

                # ReceiptDate
                receipt_date = self.validate_obj_date(rec, error, "dispatchDate")
                if receipt_date == -1:
                    is_error = True
                    break

                #Receipt Line
                for line in rec['details']:
                    line_details = []

                    temp_product = 0
                    # LINE VALIDATION ================================
                    # inwardLineOptChar1
                    if line['soLineOptChar1'] == "":
                        error["Error"] = "Field soLineOptChar1 is blank"
                        is_error = True
                        break

                    # product
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break

                    # check status code
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break

                    # check quantityReceived
                    if line['quantityShipped'] == "":
                        error["Error"] = "Field quantityShipped is blank"
                        is_error = True
                        break
                    
                    # search stock move
                    try:
                        receipt_line = request.env['stock.move'].search(['&', '&', ('origin','=',rec['soNo']),('x_studio_opt_char_1', '=', line["soLineOptChar1"]), ('state', '=', 'assigned')])
                    except Exception as e:
                        error["Error"] = "Error in searching stock move " + str(e)
                        is_error = True
                        break

                    if receipt_line['origin'] != rec['soNo']:
                        error["Error"] = "Stock Move not found"
                        is_error = True
                        break

                    # Set WMS rec no of stock move
                    receipt_line['x_wms_rec_no'] = rec['receiptNo']
                    
                    # LINE VALIDATION END ==============================================

                    # Create a new product does not exist yet, else use existing product
                    try:
                        temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                    except Exception as e:
                        error["Error"] = "Error in searching existing product " + str(e)
                        is_error = True
                        break
                        
                    if temp_product == -1:
                            error["Error"] = "Product does not exist"
                            is_error = True
                            break
                    
                    # check whether quantityShipped exceeds the demand
                    if receipt_line["product_uom_qty"] < int(line["quantityShipped"]):
                        error["Error"] = "Quantity shipped exceeds demand"
                        is_error = True
                        break
                    
                    # Create move_line and attach to stock move
                    receipt_line.move_line_ids.write({
                            "product_id": temp_product,
                            "product_uom_id": 26,
                            "location_id": 8,
                            "location_dest_id": 4,
#                             "lot_id": "",
#                             "expiration_date": ,
#                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityShipped"],
                            "company_id": 1,
#                             "state": "done",
                            "x_wms_rec_no": rec['receiptNo']
                    })
                    
                    lines.append(line["soLineOptChar1"])

                    # Check if qty received is partial or not
                    if receipt_line['product_uom_qty'] > receipt_line['quantity_done']:
                        is_partial = True

                # INDENT  ==========================

                if is_error == True:
                    self.rollback_move(rec, error, lines, "soNo")
                    break

                receipt_header['date_done'] = receipt_date
                receipt_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # if the number of details is less than the list of products in the stock picking
                # then it is a partial case
                moves = receipt_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                    is_partial = True

                # Validate receipt
                self.validate_receipt(receipt_header, is_partial)

                response_msg = "GRN updated successfully"
                # INDENT ===========================

        except Exception as e:
            error["Error"] = str(e)
            is_error = True

        if is_error == True:
            api_log['status'] = 'error'
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

        return message
    
#   POST DO ===================================================================================
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
            
        try:
            for rec in do:
                lines = []
                
                sos = self.getRecord(model="sale.order", field="name", wms=rec['soNo'])
                if sos == -1:
                    error["Error"] = "soNo does not exist"
                    is_error = True
                    break
                    
                json_valid = self.validate_obj_json(rec, error, "soNo")
                if json_valid == -1:
                    is_error = True
                    break
                    
                do_header = self.validate_obj_header(rec, error, "soNo", 2)

                if do_header == -1:
                    is_error = True
                    break
                
                dispatch_date = self.validate_obj_date(rec, error, "dispatchDate")
                if dispatch_date == 1:
                    is_error = True
                    break

                # do Line
                for line in rec['details']:
                    line_details = []
                    temp_product = 0

                    #customerPO (DIISI APA DI POSTMAN?)
    #                 if line['customerPO'] == "":
    #                     error["Error"] = "Field customerPO is blank"
    #                     is_error = True
    #                     break

                    # LINE VALIDATION =================================
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break
                        
                    if line['soLineOptChar1'] == "":
                        error["Error"] = "Field soLineOptChar1 is blank"
                        is_error = True
                        break
                    
                    if line['quantityShipped'] == "":
                        error["Error"] = "Field quantityShipped is blank"
                        is_error = True
                        break
                        
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break
                    
                    try:
                        dispatch_line = request.env['stock.move'].search(['&', '&',('origin','=',rec['soNo']),('x_studio_opt_char_1', '=', line["soLineOptChar1"]), ('state', '=', 'assigned')])
                    except Exception as e:
                        error["Error"] = 'Error in searching stock move ' + str(e)
                        is_error = True
                        break
        
                    if dispatch_line['origin'] != rec['soNo']:
                        error["Error"] = "Stock Move not found"
                        is_error = True
                        break
                    
                    # set WMS Rec No of stock move
                    dispatch_line['x_wms_rec_no'] = rec['doNo']
                    
                    # LINE VALIDATION END =================================
                        
                    # check if product exists
                    try:
                        temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                    except Exception as e:
                        error["Error"] = 'Error in searching existing product ' + str(e)
                        is_error = True
                        break
                        
                    if temp_product == -1:
                        error["Error"] = "Product does not exist"
                        is_error = True
                        break
                    
                    # check whether quantityReceived exceeds the demand
                    if dispatch_line["product_uom_qty"] < int(line["quantityShipped"]):
                        error["Error"] = "Quantity shipped exceeds demand"
                        is_error = True
                        break

                    # LOCATION ID AMA DEST ID SBLMNNYA SAMA2 1, product uom id nya tadinya 1
                    dispatch_line.move_line_ids.write({
                            "product_id": temp_product,
                            "product_uom_id": 26,
                            "location_id": 8,
                            "location_dest_id": 5,
    #                             "lot_id": "",
    #                             "expiration_date": ,
    #                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityShipped"],
                            "company_id": 1,
#                             "state": "done",
                            "x_wms_rec_no": rec['doNo']
                    })
            
                    lines.append(line["soLineOptChar1"])
                    
                    # Check partial receipt
                    if dispatch_line['product_uom_qty'] > dispatch_line['quantity_done']:
                        is_partial = True
                    
    #           INDENT===============
                if is_error == True:
                    self.rollback_move(rec, error, lines, "soNo")
                    break
                
                do_header['x_studio_dispatch_date'] = dispatch_date
                do_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # if the number of details is less than the list of products in the stock picking
                # then it is a partial case
                moves = do_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                     is_partial = True

                # Delivery Order Validate
                self.validate_delivery(do_header, sos, is_partial)
                
                response_msg = "DO updated successfully"
            
        except Exception as e:
           error["Error"] = str(e)
           is_error = True

        if is_error == True:
            api_log['status'] = 'error'
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
        
        return message
        
    # Return DO ===================================================================================    
    @http.route('/web/api/return_do', type='json', auth='user', methods=['POST'])
    def return_do(self, rcpt):
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
                 'incoming_msg': rcpt,
                 'message_type': 'DO_RET'
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
                lines = []
                
                sos = self.getRecord(model="sale.order", field="name", wms=rec['poNo'])
                if sos == -1:
                    error["Error"] = "poNo to return does not exist"
                    is_error = True
                    break
                   
                json_valid = self.validate_obj_json(rec, error, "poNo")
                if json_valid == -1:
                    is_error = True
                    break
                
                # search the stock picking based on x wms rec no
                do_header = self.validate_return_obj_header(rec, error, 2, "doNo")
                if do_header == -1:
                    is_error = True
                    break
                
                dispatch_date = self.validate_obj_date(rec, error, "receiptDate")
                if dispatch_date == 1:
                    is_error = True
                    break

                # do Line
                for line in rec['details']:
                    line_details = []
                    temp_product = 0

                    #customerPO (DIISI APA DI POSTMAN?)
    #                 if line['customerPO'] == "":
    #                     error["Error"] = "Field customerPO is blank"
    #                     is_error = True
    #                     break

                    # LINE VALIDATION =================================
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break
                        
                    if line['inwardLineOptChar1'] == "":
                        error["Error"] = "Field inwardLineOptChar1 is blank"
                        is_error = True
                        break
                    
                    if line['quantityReceived'] == "":
                        error["Error"] = "Field quantityReceived is blank"
                        is_error = True
                        break
                        
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break
                        
                    try:    
                        dispatch_line = request.env['stock.move'].search(['&', '&',('origin','=',rec['poNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"]), ('state', '=', 'assigned')])
                    except Exception as e:
                        error["Error"] = 'Error in searching stock move ' + str(e)
                        is_error = True
                        break
        
                    if dispatch_line['origin'] != rec['poNo']:
                        error["Error"] = "Stock Move not found"
                        is_error = True
                        break
                    # LINE VALIDATION END =================================
                        
                    # check if product exists
                    try:
                        temp_product = self.getRecord(model="product.product", field="default_code", wms=line['product'])
                    except Exception as e:
                        error["Error"] = 'Error in searching existing product ' + str(e)
                        is_error = True
                        break
                        
                    if temp_product == -1:
                        error["Error"] = "Product does not exist"
                        is_error = True
                        break
                    
                    # check whether quantityReceived exceeds the demand
                    if dispatch_line["product_uom_qty"] < int(line["quantityReceived"]):
                        error["Error"] = "Quantity received exceeds demand"
                        is_error = True
                        break
                    
                    # LOCATION ID AMA DEST ID SBLMNNYA SAMA2 1, product uom id nya tadinya 1
                    dispatch_line.move_line_ids.write({
                            "product_id": temp_product,
                            "product_uom_id": 26,
                            "location_id": 5,
                            "location_dest_id": 8,
    #                             "lot_id": "",
    #                             "expiration_date": ,
    #                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityReceived"],
                            "company_id": 1,
#                             "state": "done",
                            "x_wms_rec_no": rec['doNo']
                    })
            
                    lines.append(line["inwardLineOptChar1"])
                    
                    # Check partial receipt
                    if dispatch_line['product_uom_qty'] > dispatch_line['quantity_done']:
                        is_partial = True
                    
    #           INDENT===============
                if is_error == True:
                    self.rollback_move(rec, error, lines, "poNo")
                    break
                
                do_header['x_studio_dispatch_date'] = dispatch_date
                do_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # if the number of details is less than the list of products in the stock picking
                # then it is a partial case
                moves = do_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                    is_partial = True
                
                # Delivery Order Validate
                self.validate_delivery(do_header, sos, is_partial)
                
                response_msg = "DO updated successfully"
            
        except Exception as e:
           error["Error"] = str(e)
           is_error = True

        if is_error == True:
            api_log['status'] = 'error'
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

    def validate_delivery(self, do_header, sos, is_partial):
        if is_partial == False:
            do_header.action_set_quantities_to_reservation()
            so_name = do_header['origin']
            res = self.create_immediate_transfer_so(so_name)
            do_header.with_context(cancel_backorder=True)._action_done()
        else:
            do_header.with_context(cancel_backorder=False)._action_done()
            
            ret_partial = request.env['stock.picking'].search([('state','in',['assigned','waiting','confirmed']),('origin', '=', do_header['origin'])], limit=1)
            
            for pick in ret_partial:
                pick.write({'x_wms_rec_no': do_header.x_wms_rec_no, 'x_studio_doc_trans_code': do_header.x_studio_doc_trans_code})
        
        
            
        
            
