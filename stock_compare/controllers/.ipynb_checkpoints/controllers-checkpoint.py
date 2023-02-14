# -*- coding: utf-8 -*-
from odoo import http
from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
from datetime import datetime
from odoo.exceptions import UserError


class StockCompare(http.Controller):
#     # def validate_obj_date(self, rec, error, date_type):
#     #     if rec[date_type] == "":
#     #         return ""
#     #     else:
#     #         try:
#     #             obj_date = datetime.strptime(rec[date_type], '%d/%m/%Y').date()
#     #             return obj_date
#     #         except ValueError:
#     #             error["Error"] = "Wrong date format on " + date_type 
#     #             return -1
    
    @http.route('/web/api/stock_compare', type='json', auth='user', methods=['POST'])
    def create_wms_stock(self, stock):
            created = 0
            error = {}
            warn_cnt = 1
            is_error = False
            response_msg = "Failed to receive WMS stock data"
            message = {}
            line_details = []
            is_partial = False

            # Create wms stock
            try:
                api_log = request.env['api_ven.api_ven'].create({
                    'status': 'new',
                    'created_date': datetime.now(),
                    'incoming_msg': stock,
                    'message_type': 'STOCK'
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
                    'datas': base64.b64encode(bytes(str(stock), 'utf-8')),
                    'res_model': 'api_ven.api_ven',
                    'res_id': api_log['id'],
                    'mimetype': 'text/plain'
                })
            except Exception as e:
                error['Error'] = str(e)
                is_error = True

            try:
                # Loop through every line inside the stock array
                for rec in stock:
                    # Array to store x_studio_opt_char / inwardLineOptChar1 values that have been successfully validated
                    # This is used for searching stock move lines that needs to be reversed
                    lines = []
                    
                    prev_wms_stock = request.env['stock_compare.wms_stock']
                    
                    try:
                        prev_wms_stock = request.env['stock_compare.wms_stock'].search_read([])
                    except Exception as e:
                        error['Error'] = "Error creating wms stock"
                        is_error = True
                
                    
                    if prev_wms_stock:
                        request.env['stock_compare.wms_stock'].search([]).unlink()
                        request.env['stock_compare.wms_stock_line'].search([]).unlink()
                    
                    wms_stock = request.env['stock_compare.wms_stock'].create({})
                    
                    
                    wms_stock_line_model = request.env['stock_compare.wms_stock_line']
                    
                    
                    # (3) Receipt Lines
                    # (3) Loop through the “details” array
                    for line in rec['details']:

                        
                        # (3.1) Line validations (start) =========================================================
                        
                        if line['product'] == "":
                            error["Error"] = "Field product is blank"
                            is_error = True
                            break
                            
                        if line['quantity'] == "":
                            error["Error"] = "Field lot id is blank"
                            is_error = True
                            break
                        
                        if line['lotNo'] == "":
                            error["Error"] = "Field lot id is blank"
                            is_error = True
                            break
                            
                        if line['expiryDate'] == "":
                            error["Error"] = "Field expiry_date is blank"
                            is_error = True
                            break
                    
                        if line['warehouse'] == "":
                            error["Error"] = "Field warehouse is blank"
                            is_error = True
                            break
                        
                        new_stock_line_value = {
                            'wms_stock_id': wms_stock.id,
                            'product': line['product'],
                            'wms_quantity': line['quantity'],
                            'lot_id': False if line['lotNo'] == "NULL" else line['lotNo'],
                            'expiry_date': line['expiryDate'],
                            'warehouse': line['warehouse']
                        }

                        # Create activity log line
                        new_stock_line = wms_stock_line_model.create(new_stock_line_value)
                        

                    # (4) If there is any error, rollback previous stock moves and move lines by calling rollback_move()
                    if is_error == True:
                        # self.rollback_move(rec, error, lines, "poNo")
                        break
            
                    
                    response_msg = "Stock updated successfully"
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