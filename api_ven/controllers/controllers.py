from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
from datetime import datetime, timedelta
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

    # API for authentication
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
        # (2.3.1) Search whether the stock picking exists based on the origin, picking type id, and state
        try:
            obj_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec[rec_no_type]), ('picking_type_id', '=', pick_type_id), ('state', '=', 'assigned')])
        except Exception as e:
            error['Error'] = 'Error in searching stock.picking ' + str(e)
            return -1

        # If the poNo or soNo value that were found is not the same with the value from the JSON, then return error
        if obj_header['origin'] != rec[rec_no_type]:
            if rec_no_type == 'poNo':
                error["Error"] = "Receipt does not exist"
            else:
                error["Error"] = "Delivery order does not exist"
            return -1

        # (2.3.2) Set the x_wms_rec_no of the stock picking based on receiptNo (for RCPT API)
        if rec_no_type == 'poNo':
            # PO
            # set WMS rec no of stock picking
            obj_header['x_wms_rec_no'] = rec['receiptNo']
        # (2.3.2) Set the x_wms_rec_no of the stock picking based on doNo (for DO API)
        else:
            # SO
            # set WMS rec no of stock picking
            obj_header['x_wms_rec_no'] = rec['doNo']

        return obj_header

    def validate_obj_json(self, rec, error, rec_no_type):
        # (2.2.1) Check poNo (for RCPT API) or soNo (for DO API) is null or not
        if rec[rec_no_type] == "":
            error["Error"] = "Field " + rec_no_type + " is blank"  
            return -1
        # (2.2.2) Check documentTransCode is null or not
        if rec['documentTransCode'] == "":
            error["Error"] = "Field documentTransCode is blank"
            return -1
        # (2.2.3) Check WMS Receipt No (for PO API) 
        if rec_no_type == 'poNo':
            if rec['receiptNo'] == "" or 'receiptNo' not in rec:
                error["Error"] = "Field WMS Receipt Number is blank"
                return -1
        # (2.2.3) Check WMS DO No (for DO API)
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

    
    def rollback_move(self, rec, error, lines, rec_no_type):
        # (4) Rollback previous stock move lines
        if lines:
            # if there are previous products
            # loop through the list, search for the stock move, unreserve the stock move
            for line in lines:
                curr_move = request.env['stock.move'].search(['&', '&', ('origin','=', rec[rec_no_type]),('x_studio_opt_char_1', '=', str(line)), ('state', '=', 'assigned')])
                
                curr_move.move_line_nosuggest_ids.write({'qty_done': 0})
    
    # PO (CRT_RCPT API) ===================================================================================
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

            # Create api log
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

            # Create incoming txt
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
                # Loop through every line inside the rcpt array
                for rec in rcpt:
                    # (1) Array to store x_studio_opt_char / inwardLineOptChar1 values that have been successfully validated
                    # This is used for searching stock move lines that needs to be reversed
                    lines = []
                    
                    # (2) Validations (start)

                    # (2.1) Check whether po no exists
                    
                    po = request.env['purchase.order'].search([('name', '=', rec['poNo'])], limit=1)
                    curr_company_id = po.company_id
                    if not po:
                        error["Error"] = "receipt no does not exist"
                        is_error = True
                        break
                    
                    # (2.2) Call validate_obj_json() to validate poNo, documentTransCode, and receiptNo
                    json_valid = self.validate_obj_json(rec, error, "poNo")
                    if json_valid == -1:
                        is_error = True
                        break
                    
                    # (2.3) Call validate_obj_header() to validate the stock picking and set the x_wms_rec_no value
                    # Changing information (VL) ==> Need to create validation about picking type list.
                    # Because different company have different picking_list_id
                    receipt_header = []
                    if curr_company_id.id == 1: 
                        receipt_header = self.validate_obj_header(rec, error, "poNo", 1)
                    else:
                        receipt_header = self.validate_obj_header(rec, error, "poNo", 7)
                    if receipt_header == -1:
                        is_error = True
                        break
                    
                    # (2.4) Call validate_obj_date to validate the date format
                    receipt_date = self.validate_obj_date(rec, error, "receiptDate")
                    if receipt_date == -1:
                        is_error = True
                        break

                    # (2) Validations (end)
                    
                    # (3) Receipt Lines
                    # (3) Loop through the “details” array
                    for line in rec['details']:
                        line_details = []
                        
                        temp_product = 0

                        
                        # (3.1) Line validations (start) =========================================================
                        
                        # (3.1.1) Check inwardLineOptChar1
                        if line['inwardLineOptChar1'] == "":
                            error["Error"] = "Field inwardLineOptChar1 is blank"
                            is_error = True
                            break
                        
                        # (3.1.1) Check product
                        if line['product'] == "":
                            error["Error"] = "Field product is blank"
                            is_error = True
                            break
                            
                        # (3.1.1) Check status code
                        if line['stockStatusCode'] == "":
                            error["Error"] = "Field stockStatusCode is blank"
                            is_error = True
                            break
                    
                        # (3.1.1) Check quantityReceived
                        if line['quantityReceived'] == "":
                            error["Error"] = "Field quantityReceived is blank"
                            is_error = True
                            break
                        
                        # (3.1.2) Search the corresponding stock move based on origin (poNo), x_studio_opt_char_1, and state
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
                        
                        # (3.1.3) Set the x_wms_rec_no of the stock move based on receiptNo
                        receipt_line['x_wms_rec_no'] = rec['receiptNo']
                            
                        # (3.1.4) Check whether the product exists or not
                        
                        try:
                            temp_product = receipt_line.move_line_ids.product_id
                        except Exception as e:
                            error["Error"] = "Error in searching existing product || " + str(e)
                            is_error = True
                            break
                            
                        if not temp_product:
                            error["Error"] = "Product does not exist"
                            is_error = True
                            break
                        
                        # (3.1.5) Check whether quantityReceived exceeds the demand
                        if receipt_line["product_uom_qty"] < int(line["quantityReceived"]):
                            error["Error"] = "Quantity received exceeds demand"
                            is_error = True
                            break
                            
                        # (3.1) Line validations (end) =====================
                        
                        # Checking if the order is using LOT_Number or Serial Number
                        
                        # (3.2) Update a new move stock line
                        receipt_line.move_line_ids.write({
                            "product_id": temp_product.id,
                            "product_uom_id": receipt_line.move_line_ids.product_uom_id.id,
                            "location_id": receipt_line.move_line_ids.location_id.id,
                            "location_dest_id": receipt_line.move_line_ids.location_dest_id.id,
                            "x_stock_status_code": line["stockStatusCode"],
                            "x_wms_lot_records": line['lotNo'],
                            "qty_done": line["quantityReceived"],
                            "company_id": curr_company_id.id,
                            # "state": "done",
                            "x_wms_rec_no": rec['receiptNo']
                        })
                            
                        # (3.3) Append the inwardLineOptChar1 / x_studio_opt_char1 (current line number) to the lines array
                        lines.append(line["inwardLineOptChar1"])
        
                        # (3.4) Check if quantity done is partial or not
                        if receipt_line['product_uom_qty'] > receipt_line['quantity_done']:
                            is_partial = True

                    # (4) If there is any error, rollback previous stock moves and move lines by calling rollback_move()
                    if is_error == True:
                        self.rollback_move(rec, error, lines, "poNo")
                        break
                    
            
                    # (5) Set the stock picking's date_done and x_studio_doc_trans_code
                    receipt_header['date_done'] = receipt_date
                    receipt_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                    
                    
                    # (6) If the contents of "details" array is less than the number of products / stock moves in the stock picking
                    # then it is a partial case
                    moves = receipt_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                    if len(rec['details']) < len(moves):
                        is_partial = True
                    
                    # (7) Call validate_receipt to validate the receipt
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

            # Create response txt
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
            # (7.1.1) If there are no partial cases, create immediate transfer
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
        # (7.1) If there are no partial cases
        if is_partial == False:
            # If there is no partial received items, then change the stock picking to stock.immediate (similar to pushing a button). 
            # When stock picking change to stock immediate, it will be picked urgently and backorder cannot be created. 
            # So, each product has to fullfil the required qty. Then, the picking status will be changed to done.
            po_name = receipt_header['origin']
            # (7.1.1) Call create_immediate_transfer()
            res = self.create_immediate_transfer(po_name)
            receipt_header.with_context(cancel_backorder=True)._action_done()
            
        # (7.2) If there is a partial case
        else:
            # If there is a partial order, we do not change it to stock.immediate as we want to create backorder. 
            # So, we get the stock.picking, and process while also create a backorder.
            receipt_header.with_context(cancel_backorder=False)._action_done()

            
            
    # (2.3) Stock picking validation for returns (search based on wms rec no)
    # obj_header validation for po and so return api
    def validate_return_obj_header(self, rec, error, no_typepick_type_id, rec_no_type):
        try:
            # (2.3.1) Search whether the stock picking exists based on the x_wms_rec_no (receiptNo) and state for PO return
            # (2.3.1) Search whether the stock picking exists based on the x_wms_rec_no (doNo) and state for SO return
            obj_header = request.env["stock.picking"].search(['&', ('x_wms_rec_no', '=', rec[rec_no_type]), ('state', '=', 'assigned')])[-1]
            
        except Exception as e:
            error["Error"] = 'Error in searching stock picking ' + str(e)
            return -1

        if obj_header['x_wms_rec_no'] != rec[rec_no_type]:
            # (2.3.2) If x_wms_rec_no is not found, return error message “Return receipt does not exist” for PO return
            # (2.3.2) If x_wms_rec_no is not found, return error message “Return delivery order does not exist” for SO return
            if pick_type_id == 1 :
                error["Error"] = "Return receipt does not exist"
            else:
                error["Error"] = "Return delivery order does not exist"
            return -1

        return obj_header
    
    
    
    # PO-RETURN (CRT_RCPT_RET API) ===================================================================================
    @http.route('/web/api/return_rcpt', type='json', auth='user', methods=['POST'])
    def return_rcpt(self, do):
        created = 0
        error = {}
        warn_cnt = 1
        rcpt_lines = []        
        is_error = False
        response_msg = "Failed to create DO!"
        message = {}
        line_details = []
        is_partial = False        

        # Create API log
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

        # Create incoming txt
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
            # Loop through every record in “do” array from the JSON that was sent from WMS
            for rec in do:
                # (1) Declare “lines” array to store soLineOptChar1 or x_wms_rec_no values that have been successfully validated
                lines = []
                
                # (2) Validations
                stock_picking = request.env['stock.picking'].search([('name','=',rec['soNo'])], limit=1)                
                # raise UserError(stock_picking);
                curr_company_id = stock_picking.company_id
                if not stock_picking:
                    error["Error"] = "Stock move does not exist"
                    is_error = True
                    break
                
                # Call validate_obj_json()
                json_valid = self.validate_obj_json(rec, error, "soNo")
                if json_valid == -1:
                    is_error = True
                    break
                    
                # Call validate_return_obj_header()
                receipt_header = []
                if curr_company_id.id == 1: 
                    receipt_header = self.validate_return_obj_header(rec, error, 1, "receiptNo")
                else:
                    receipt_header = self.validate_return_obj_header(rec, error, 7, "receiptNo")
                if receipt_header == -1:
                    is_error = True
                    break

                # Call validate_obj_date()
                receipt_date = self.validate_obj_date(rec, error, "dispatchDate")
                if receipt_date == -1:
                    is_error = True
                    break

                # (3) Loop through the “details” array
                for line in rec['details']:
                    line_details = []

                    temp_product = 0
                    
                    
                    # (3.1) Line validations (start) =========================================================
                    
                    # (3.1.1) Check soLineOptChar1
                    if line['soLineOptChar1'] == "":
                        error["Error"] = "Field soLineOptChar1 is blank"
                        is_error = True
                        break

                    # (3.1.1) Check product
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break

                    # (3.1.1) Check stockStatusCode
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break

                    # (3.1.1) Check quantityShipped
                    if line['quantityShipped'] == "":
                        error["Error"] = "Field quantityShipped is blank"
                        is_error = True
                        break
                    
                    # (3.1.2) Search the corresponding stock move based on origin (soNo), 
                    # x_studio_opt_char_1 (soLineOptChar1), and state
                    try:
                        receipt_line = request.env['stock.move'].search(['&', '&', ('reference','=',rec['soNo']),('x_studio_opt_char_1', '=', line["soLineOptChar1"]), ('state', '=', 'assigned')])
                    except Exception as e:
                        error["Error"] = "Error in searching stock move " + str(e)
                        is_error = True
                        break

                    if receipt_line['reference'] != rec['soNo']:
                        error["Error"] = "Stock Move not found"
                        is_error = True
                        break

                    # (3.1.3) Set the x_wms_rec_no of the stock move based on receiptNo
                    receipt_line['x_wms_rec_no'] = rec['receiptNo']

                    # (3.1.4) Check whether the product exists or not
                    try:
                        temp_product = receipt_line.move_line_ids.product_id
                    except Exception as e:
                        error["Error"] = "Error in searching existing product " + str(e)
                        is_error = True
                        break
                        
                    if temp_product == -1:
                            error["Error"] = "Product does not exist"
                            is_error = True
                            break
                        
                    
                    # (3.1.5)Check whether quantityShipped exceeds demand
                    if receipt_line["product_uom_qty"] < int(line["quantityShipped"]):
                        error["Error"] = "Quantity shipped exceeds demand"
                        is_error = True
                        break
                        
                    # (3.1) Line validations (start) =============================================
                            
                    # (3.2) Use write() to create a new stock move line for this product / stock move
                    receipt_line.move_line_ids.write({
                            "product_id": temp_product.id,
                            "product_uom_id": receipt_line.move_line_ids.product_uom_id.id,
                            "location_id": receipt_line.move_line_ids.location_id.id,
                            "location_dest_id": receipt_line.move_line_ids.location_dest_id.id,
#                             "lot_id": "",
#                             "expiration_date": ,
#                             "lot_id": temp_lot['id'],
                            "qty_done": line["quantityShipped"],
                            "company_id": curr_company_id.id,
#                             "state": "done",
                            "x_wms_rec_no": rec['receiptNo'],
                            "x_stock_status_code": line["stockStatusCode"],
                            "x_wms_lot_records": line["lotNo"]
                    })
                    
                    # (3.3) Append the soLineOptChar1 / x_studio_opt_char1 (current line number) to the lines array
                    lines.append(line["soLineOptChar1"])

                    # (3.4) Check if quantity done is partial or not
                    if receipt_line['product_uom_qty'] > receipt_line['quantity_done']:
                        is_partial = True

                # (4) If there is any error, rollback previous stock moves and move lines by calling rollback_move()
                if is_error == True:
                    self.rollback_move(rec, error, lines, "soNo")
                    break

                # (5) Set the stock picking's date_done and x_studio_doc_trans_code
                receipt_header['date_done'] = receipt_date
                receipt_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # (6) If the contents of "details" array is less than the number of products/stock moves in the stock picking 
                # then it is a partial case
                moves = receipt_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                    is_partial = True

                # (7) Call validate_receipt()
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

        # # Create response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(message), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
        
        return message
        
    
#   DO API (CRT_DO API) ===================================================================================
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
        
        # Send API Log
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
        
        # Create incoming txt
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
            # Loop through every line in "do" array
            for rec in do:
                # (1) Array to store x_studio_opt_char / inwardLineOptChar1 values that have been successfully validated
                # This is used for searching stock move lines that needs to be reversed
                lines = []
                
                
                # (2) Validations (start)
                
                # (2.1) Validate soNo
                sos = request.env['sale.order'].search([('name', '=', rec['soNo'])], limit=1)
                curr_company_id = sos.company_id
                if not sos:
                    error["Error"] = "soNo does not exist"
                    is_error = True
                    break
                    
                # (2.2) Call validate_obj_json() to validate soNo, documentTransCode, and doNo (WMS DO No)  
                json_valid = self.validate_obj_json(rec, error, "soNo")
                if json_valid == -1:
                    is_error = True
                    break
                    
                
                # (2.3) Call validate_obj_header() to validate the stock picking and set the x_wms_rec_no value
                do_header = []
                # obj_header = request.env["stock.picking"].search(['&','&',('origin', '=', rec['soNo']), ('picking_type_id', '=', 2), ('state', '=', 'assigned')])
                # raise UserError(f"obj_header: {obj_header}")
                if curr_company_id.id == 1:
                    do_header = self.validate_obj_header(rec, error, "soNo", 2)
                else:
                    do_header = self.validate_obj_header(rec, error, "soNo", 8)
                if do_header == -1:
                    is_error = True
                    break
                
                # raise UserError(f"713")
                # (2.4) Call validate_obj_date() to validate the date format
                dispatch_date = self.validate_obj_date(rec, error, "dispatchDate")
                if dispatch_date == 1:
                    is_error = True
                    break

                # (2) Validations (end)
                    
                    
                # (3) Loop through the “details” array
                for line in rec['details']:
                    line_details = []
                    temp_product = 0

                    
                    # (3.1) Line validations (start) =========================================================

                    # (3.1.1) Check product
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check soLineOptChar1
                    if line['soLineOptChar1'] == "":
                        error["Error"] = "Field soLineOptChar1 is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check quantityShipped
                    if line['quantityShipped'] == "":
                        error["Error"] = "Field quantityShipped is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check stockStatusCode
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break

                    # (3.1.2) Search the corresponding stock move
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
                    
                    # Set x_wms_rec_no of stock move based on doNo
                    dispatch_line['x_wms_rec_no'] = rec['doNo']
                    
                        
                    # (3.1.4) Check whether the product exists or not
                    try:
                        temp_product = dispatch_line.move_line_ids.product_id
                    except Exception as e:
                        error["Error"] = "Error in searching existing product || " + str(e)
                        is_error = True
                        break
                            
                    if not temp_product:
                        error["Error"] = "Product does not exist"
                        is_error = True
                        break
                    
                    # Check whether quantityShipped exceeds the demand
                    if dispatch_line["product_uom_qty"] < int(line["quantityShipped"]):
                        error["Error"] = "Quantity shipped exceeds demand"
                        is_error = True
                        break

                    # (3.1) Line validations (end) ============================
                    
                    # (3.2) Create a new stock move line for this product / stock move
                    # LOCATION ID AMA DEST ID SBLMNNYA SAMA2 1, product uom id nya tadinya 1
                    dispatch_line.move_line_ids.write({
                        "product_id": temp_product.id,
                        "product_uom_id": dispatch_line.move_line_ids.product_uom_id.id,
                        "location_id": dispatch_line.move_line_ids.location_id.id,
                        "location_dest_id": dispatch_line.move_line_ids.location_dest_id.id,
                        # "expiration_date": ,
                        "x_wms_lot_records": line['lotNo'],
                        "qty_done": line["quantityShipped"],
                        "company_id": curr_company_id.id,
                        # "state": "done",
                        "x_wms_rec_no": rec['doNo'],
                        "x_stock_status_code": line["stockStatusCode"],
                        "x_wms_lot_records": line["lotNo"]
                    })
            
                    # (3.3) Append the soLineOptChar1 / x_studio_opt_char1 (current line number) to the lines array
                    lines.append(line["soLineOptChar1"])
                    
                    # (3.4) Check if quantity done is partial or not
                    if dispatch_line['product_uom_qty'] > dispatch_line['quantity_done']:
                        is_partial = True
                    
                
                # (4) Rollback previous stock move lines / products if there is an error
                if is_error == True:
                    self.rollback_move(rec, error, lines, "soNo")
                    break
                
                # (5) Set the stock picking's x_studio_dispatch_date and x_studio_doc_trans_code
                do_header['x_studio_dispatch_date'] = dispatch_date
                do_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # (6) If the number of details is less than the list of products / stock moves in the stock picking
                # then it is a partial case
                moves = do_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                     is_partial = True

                # (7) Call validate_delivery()
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

        # Create response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(message), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'mimetype': 'text/plain'
        })
        
        return message
        
        
        
    # Return DO (CRT_DO_RET API) ===================================================================================
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
        
        # Create API log
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
        
        # Create incoming txt
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
            # Loop through every record in rcpt array
            for rec in rcpt:
                # (1) Declare “lines” array to store inwardLineOptChar1 or x_wms_rec_no values that have been successfully validated
                lines = []
                
                # (2) Validations
                # (2.1) Check whether po no (this field actually stores the SO no value) exists 
                stock_picking = request.env['stock.picking'].search([('name','=',rec['poNo'])], limit=1)
                curr_company_id = stock_picking.company_id
                if not stock_picking:
                    error["Error"] = "Stock move does not exist"
                    is_error = True
                    break
                   
                # (2.2) Call validate_obj_json()
                json_valid = self.validate_obj_json(rec, error, "poNo")
                if json_valid == -1:
                    is_error = True
                    break
                
                # (2.3) Call validate_return_obj_header()
                do_header = []
                if curr_company_id.id == 1: 
                    do_header = self.validate_return_obj_header(rec, error, 2, "doNo")
                else:
                    do_header = self.validate_return_obj_header(rec, error, 8, "doNo")
                if do_header == -1:
                    is_error = True
                    break
                
                # (2.4) Call validate_obj_date()
                dispatch_date = self.validate_obj_date(rec, error, "receiptDate")
                if dispatch_date == 1:
                    is_error = True
                    break

                # (3) Loop through the “details” array
                for line in rec['details']:
                    line_details = []
                    temp_product = 0

    
                    # (3.1) Line validations (start) =========================================================
                    # (3.1.1) Check product
                    if line['product'] == "":
                        error["Error"] = "Field product is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check inwardLineOptChar1
                    if line['inwardLineOptChar1'] == "":
                        error["Error"] = "Field inwardLineOptChar1 is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check quantityReceived
                    if line['quantityReceived'] == "":
                        error["Error"] = "Field quantityReceived is blank"
                        is_error = True
                        break
                    
                    # (3.1.1) Check stockStatusCode
                    if line['stockStatusCode'] == "":
                        error["Error"] = "Field stockStatusCode is blank"
                        is_error = True
                        break
                    
                    # (3.1.2) Try to search the corresponding stock move based on origin (poNo), x_studio_opt_char_1 
                    # (inwardLineOptChar1 ), and state
                    try:    
                        dispatch_line = request.env['stock.move'].search(['&', '&',('reference','=',rec['poNo']),('x_studio_opt_char_1', '=', line["inwardLineOptChar1"]), ('state', '=', 'assigned')])
                    except Exception as e:
                        error["Error"] = 'Error in searching stock move ' + str(e)
                        is_error = True
                        break
        
                    if dispatch_line['reference'] != rec['poNo']:
                        error["Error"] = "Stock Move not found"
                        is_error = True
                        break
                        
                    # (3.1.4) Try to search for the product
                    try:
                        temp_product = dispatch_line.move_line_ids.product_id
                    except Exception as e:
                        error["Error"] = 'Error in searching existing product ' + str(e)
                        is_error = True
                        break
                        
                    if not temp_product:
                        error["Error"] = "Product does not exist"
                        is_error = True
                        break
                        
                    temp_product = dispatch_line.move_line_ids.product_id
                    
                    # (3.1.5) Check whether quantityReceived exceeds demand because this is not allowed
                    if dispatch_line["product_uom_qty"] < int(line["quantityReceived"]):
                        error["Error"] = "Quantity received exceeds demand"
                        is_error = True
                        break
                    
                    # (3.1) Line validations (end) =========================================================
                    
                    
                    # (3.2) Use write() to create a new stock move line for this product
                    # LOCATION ID AMA DEST ID SBLMNNYA SAMA2 1, product uom id nya tadinya 1
                    dispatch_line.move_line_ids.write({
                            "product_id": temp_product.id,
                            "product_uom_id": dispatch_line.move_line_ids.product_uom_id.id,
                            "location_id": dispatch_line.move_line_ids.location_id.id,
                            "location_dest_id": dispatch_line.move_line_ids.location_dest_id.id,
                            # "lot_id": "",
                            # "expiration_date": ,
                            # "lot_id": temp_lot['id'],
                            "qty_done": line["quantityReceived"],
                            "company_id": curr_company_id.id,
                            # "state": "done",
                            "x_wms_rec_no": rec['doNo'],
                            "x_stock_status_code": line["stockStatusCode"],
                            "x_wms_lot_records": line["lotNo"]
                    })
            
                    # (3.3) Append the inwardLineOptChar1 / x_studio_opt_char1 (current line number) to the lines array
                    lines.append(line["inwardLineOptChar1"])
                    
                    # (3.4) Check if quantity done is partial or not
                    if dispatch_line['product_uom_qty'] > dispatch_line['quantity_done']:
                        is_partial = True
                
                # (4) If there is any error, rollback previous stock moves and move lines by calling rollback_move()
                if is_error == True:
                    self.rollback_move(rec, error, lines, "poNo")
                    break
                    
                # (5) Set the stock picking's x_studio_dispatch_date and x_studio_doc_trans_code
                do_header['x_studio_dispatch_date'] = dispatch_date
                do_header['x_studio_doc_trans_code'] = rec["documentTransCode"]
                
                # (6) If the contents of "details" array is less than the number of products/stock moves in the stock picking 
                # then it is a partial case
                moves = do_header['move_ids_without_package'].search([('state', '=', 'assigned')])
                if len(rec['details']) < len(moves):
                    is_partial = True
                
                # Call validate_delivery()
                self.validate_delivery(do_header, stock_picking, is_partial)
                
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
    
    # (7.1.1) If there are no partial cases, create immediate transfer
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
    
#     def create_immediate_transfer_so(self, so_name):
#         # (7.1.1) If there are no partial cases, create immediate transfer
#         so_obj = request.env['sale.order'].search([('name', '=', so_name )])
        
#         immediate_transfer_line_ids = []
        
#         for picking in so_obj.picking_ids:
#             if picking['state'] == 'assigned':
#                 immediate_transfer_line_ids.append([0, False, {
#                     'picking_id': picking.id,
#                     'to_immediate': True
#                 }])

#         res = request.env['stock.immediate.transfer'].create({
#             'pick_ids': [(4, p.id) for p in so_obj.picking_ids],
#             'show_transfers': False,
#             'immediate_transfer_line_ids': immediate_transfer_line_ids
#         })
#         return res

    def validate_delivery(self, do_header, sos, is_partial):
        # (7.1) If there are no partial cases
        if is_partial == False:
            do_header.action_set_quantities_to_reservation()
            so_name = do_header['origin']
            # (7.1.1) If there are no partial cases, create immediate transfer
            res = self.create_immediate_transfer_so(so_name)
            do_header.with_context(cancel_backorder=True)._action_done()
        # (7.2) If there is a partial case
        else:
            do_header.with_context(cancel_backorder=False)._action_done()
            
            ret_partial = request.env['stock.picking'].search([('state','in',['assigned','waiting','confirmed']),('origin', '=', do_header['origin'])], limit=1)
            
            for pick in ret_partial:
                pick.write({'x_wms_rec_no': do_header.x_wms_rec_no, 'x_studio_doc_trans_code': do_header.x_studio_doc_trans_code})
    
    @http.route('/web/api/stock_adjustment', type='json', auth='user', methods=['POST'])
    def stock_adjustment(self, adjustList):
        # raise UserError('test')
        create = 0
        error = {}
        is_error = False
        response_msg = "Failed to receive WMS stock adjustment data"
        message = {}
        api_log = request.env['api_ven.api_ven']
        
        # Create api log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': adjustList,
                'message_type': 'ADJUST'
            })

            api_log['status'] = 'process'
        except Exception as e:
            error['Error'] = str(e)
            is_error = True

        # Create incoming txt
        try:
            api_log['incoming_txt'] = request.env['ir.attachment'].create({
                'name': str(api_log['name']) + '_in.txt',
                'type': 'binary',
                'datas': base64.b64encode(bytes(str(adjustList), 'utf-8')),
                'res_model': 'api_ven.api_ven',
                'res_id': api_log['id'],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
        
        # ==========================================
        adjustList = adjustList[0].get('adj', [])
        
        # Looping        
        try:
            # Validation            
            if not adjustList:                
                error["Error"] = 'adjustList is empty'
                is_error = True
                    
            # Searching existing model                                
            for adjust_item in adjustList:
                if is_error:
                    break
                        
                product_id = adjust_item.get('product')
                if not product_id:
                    error["Error"] = 'Product ID is missing in adjustList'
                    is_error = True
                    break                                        
                    
                quantity = adjust_item.get('qtyOnHand')
        
                # Update the stock different + apply auto confirm
                if quantity is not None:                    
                    product = request.env['stock.quant'].search([('product_id', '=', product_id)], limit=1)
                    if product:
                        product.write({'quantity': quantity})
                        response_msg = "Stock adjusted successfully"
                    else:
                        error['Error'] = f'Product not found with ID {product_id}'
                        is_error = True
                else:
                    error['Error'] = 'Quantity is missing for product with ID ' + str(product_id)
                    is_error = True
        
            if not is_error:
                response_msg = "Stock adjusted successfully"
                
        except Exception as e:
            error['Error'] = str(e)
            is_error = True                                
        # ==========================================

        # # Print out only specified fields in a model
        # products = request.env['sale.order'].sudo().search([])        
        
        # # Prepare response data
        # response_data = []
        # for product in products:
        #     # Create a dictionary with only the specified fields
        #     product_dict = {
        #         'partner_id': product.partner_id.id,
        #         'partner_invoice_id': product.partner_invoice_id.id if product.partner_invoice_id else None,
        #         'partner_shipping_id': product.partner_shipping_id.id if product.partner_shipping_id else None,
        #         'pricelist_id': product.pricelist_id.id if product.pricelist_id else None,
        #     }
            
        #     response_data.append(product_dict)
        
        # response = {'message': 'Success', 'data': response_data}

        # Print out id, currency_id, and invoice_ids of the res.partner model

        # Update API status
        if is_error == True:
            api_log['status'] = 'error'
        else:
            Response.status = "200"
            api_log['status'] = 'success'

        message = {
            'response': response_msg,
            'message': error
        } 

        # Create Response Date
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
        
        # return message
        return response

    @http.route('/web/api/get_product_by_id', type='json', auth='user', methods=['POST'])
    def get_product(self):
        # Retrieve the product data from the JSON payload
        product_data = request.jsonrequest.get('product', {})
        if not product_data:
            return {'message': 'Invalid data format', 'data': {}}
        default_code = product_data.get('default_code')
        name = product_data.get('name')
        categ_id = product_data.get('categ_id')
        if not default_code:
            return {'message': 'Default code is required', 'data': {}}
        # Retrieve the product.template record based on the default code
        product_template = request.env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if not product_template:
            return {'message': 'Product not found', 'data': {}}
        # Get all field values of the product_template
        response_data = product_template.read()[0]
 
        response = {'message': 'Success', 'data': response_data}
        return response

    @http.route('/web/api/update_product_name', type='json', auth='user', methods=['POST'])
    def update_product_name(self):
        # Retrieve the product data from the JSON payload
        product_data = request.jsonrequest.get('product', {})
        if not product_data:
            return {'message': 'Invalid data format', 'data': {}}
        default_code = product_data.get('default_code')
        new_name = product_data.get('name')
    
        if not default_code or not new_name:
            return {'message': 'Default code and new name are required', 'data': {}}
    
        # Retrieve the product.template record based on the default code
        # product_template = request.env['product.template'].search([('default_code', '=', default_code)], limit=1)

        # Set context with allowed company IDs
        context = dict(request.env.context, allowed_company_ids=request.env.user.company_ids.ids)
    
        # Retrieve the product.template record based on the default code
        product_template = request.env['product.template'].with_context(context).search([('default_code', '=', default_code)], limit=1)
        
        if not product_template:
            return {'message': 'Product not found', 'data': {}}
    
        # Update the product name
        product_template.write({'name': new_name})
    
        # Retrieve the updated product data
        response_data = product_template.read()[0]
    
        response = {'message': 'Success', 'data': response_data}
        return response

    @http.route('/web/api/update_product_categ', type='json', auth='user', methods=['POST'])
    def update_product_categ(self):
        # Retrieve the product data from the JSON payload
        product_data = request.jsonrequest.get('product', {})
        if not product_data:
            return {'message': 'Invalid data format', 'data': {}}
    
        default_code = product_data.get('default_code')
        new_categ_id = product_data.get('categ_id')
    
        # Validate required fields
        if not default_code or not new_categ_id:
            return {'message': 'Default code and category ID are required', 'data': {}}

        # Set context with allowed company IDs
        context = dict(request.env.context, allowed_company_ids=request.env.user.company_ids.ids)
    
        # Retrieve the product.template record based on the default code
        product_template = request.env['product.template'].with_context(context).search([('default_code', '=', default_code)], limit=1)
        
        if not product_template:
            return {'message': 'Product not found', 'data': {}}
        
        # Validate the category ID
        category = request.env['product.category'].with_context(context).browse(new_categ_id)
        if not category.exists():
            return {'message': 'Invalid category ID', 'data': {}}

        # Validate the category ID
        category = request.env['product.category'].with_context(context).browse(new_categ_id)
        if not category.exists():
            return {'message': 'Invalid category ID', 'data': {}}
    
        # Update the category ID on the product
        product_template.write({'categ_id': new_categ_id})
    
        # Get all field values of the product_template
        response_data = product_template.read()[0]
    
        response = {'message': 'Categ_id updated successfully', 'data': response_data}
        return response


    @http.route('/web/api/update_product', type='json', auth='user', methods=['POST'])
    def update_product(self):
        # Retrieve the product data from the JSON payload
        product_data = request.jsonrequest.get('product', {})
        if not product_data:
            return {'message': 'Invalid data format', 'data': {}}
    
        default_code = product_data.get('default_code')
        name = product_data.get('name')
        # categ_id = product_data.get('categ_id')
    
        if not default_code or not name:
            return {'message': 'Default code and new name are required', 'data': {}}
    
        # Retrieve the product.template re  cord based on the default code
        # product_template = request.env['product.template'].with_context(allowed_company_ids=[1]).search([('default_code', '=', default_code)], limit=1)

        # Set context with allowed company IDs
        context = dict(request.env.context, allowed_company_ids=request.env.user.company_ids.ids)
    
        # Retrieve the product.template record based on the default code
        product_template = request.env['product.template'].with_context(context).search([('default_code', '=', default_code)], limit=1)

        if not product_template:
            return {'message': 'Product not found', 'data': {}}
      
        # Update the product name
        product_template.write({'name': name})
        # product_template.write({'categ_id': categ_id})
    
        response_data = product_template.read()[0]
        response = {'message': 'Product name updated successfully', 'data': response_data}
    
        return response