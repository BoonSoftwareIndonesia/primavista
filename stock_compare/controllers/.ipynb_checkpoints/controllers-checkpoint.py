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

            # Create API Log
            try:
                api_log = request.env['api_ven.api_ven'].create({
                    'status': 'new',
                    'created_date': datetime.now(),
                    'incoming_msg': ivdList,
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
                # Loop through every line inside the ivdList array
                for rec in ivdList:
                    # lines = []
                    
                    # Assign the wms_stock model to a variable called "prev_wms_stock"
                    prev_wms_stock = request.env['stock_compare.wms_stock']
                    
                    # Try to get all existing wms stock
                    try:
                        prev_wms_stock = request.env['stock_compare.wms_stock'].search_read([])
                    except Exception as e:
                        error['Error'] = "Error creating wms stock"
                        is_error = True
                
                    # If a WMS stock already exist, unlink the wms stock and all stock lines 
                    # because everytime we receive the inventory data from WMS, the previous data needs to be deleted
                    # and replaced with the new data
                    if prev_wms_stock:
                        request.env['stock_compare.wms_stock'].search([]).unlink()
                        request.env['stock_compare.wms_stock_line'].search([]).unlink()
                    
                    # Check if ownerCode is null
                    if line['ownerCode'] == "":
                            error["Error"] = "Field owner code is blank"
                            is_error = True
                            break
                    
                    # Check if documentType is null
                    if line['documentType'] == "":
                        error["Error"] = "Field document type is blank"
                        is_error = True
                        break

                    # Create a new wms stock
                    wms_stock = request.env['stock_compare.wms_stock'].create({})
                    
                    # Assign the wms_stock_line model to a variable called "wms_stock_line_model"
                    wms_stock_line_model = request.env['stock_compare.wms_stock_line']
                    
                    # Loop through the "ivd" array. This contains every product in WMS
                    for line in rec['ivd']:
                        # Line validations (start) =========================================================
#                         if line['warehouseCode'] == "":
#                             error["Error"] = "Field warehouse code is blank"
#                             is_error = True
#                             break
                        
#                         if line['ownerCode'] == "":
#                             error["Error"] = "Field owner code is blank"
#                             is_error = True
#                             break
                            
#                         if line['product'] == "":
#                             error["Error"] = "Field product is blank"
#                             is_error = True
#                             break
                            
#                         if line['lotNumber'] == "":
#                             error["Error"] = "Field lot number is blank"
#                             is_error = True
#                             break
                            
#                         if line['serialNumber'] == "":
#                             error["Error"] = "Field serial number is blank"
#                             is_error = True
#                             break
                        
#                         if line['expiryDate'] == "":
#                             error["Error"] = "Field expiry date is blank"
#                             is_error = True
#                             break
                        
#                         if line['qtyOnHand'] == "":
#                             error["Error"] = "Field quantity on hand is blank"
#                             is_error = True
#                             break
                        
#                         if line['stockStatusCode'] == "":
#                             error["Error"] = "Field stock status code is blank"
#                             is_error = True
#                             break
                            
                            
                            
                            
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
                        
                        # Assign the values for a new stock line for this product
                        
                        # new_stock_line_value = {
                        #     'wms_stock_id': wms_stock.id,
                        #     'product': line['product'],
                        #     'wms_quantity': line['qtyOnHand'],
                        #     'lot_id': False if line['lotNumber'] == "NULL" else line['lotNumber'],
                        #     'expiry_date': line['expiryDate'],
                        #     'location': line['warehouseCode'],
                        #     'warehouse': line['warehouseCode']
                        # }
                        
                        # new_stock_line_value = {
                        #     'wms_stock_id': wms_stock.id,
                        #     'product': line['product'],
                        #     'wms_quantity': line['quantity'],
                        #     'lot_id': False if line['lotNo'] == "NULL" else line['lotNo'],
                        #     'expiry_date': line['expiryDate'],
                        #     'location': line['warehouse'],
                        #     'warehouse': line['warehouse']
                        # }
                        
                        new_stock_line_value = {
                            'wms_stock_id': wms_stock.id,
                            'product': line['product'],
                            'wms_quantity': line['quantity'],
                            'lot_id': False if line['lotNo'] == "NULL" else line['lotNo'],
                            'lot_name': False if line['lotNo'] == "NULL" else line['lotNo'],
                            'expiry_date': line['expiryDate'],
                            'location': line['warehouse'],
                            'warehouse': line['warehouse']
                        }

                        # Create a new stock line for this product
                        new_stock_line = wms_stock_line_model.create(new_stock_line_value)
                        

                    # If there is any error
                    if is_error == True:
                        # self.rollback_move(rec, error, lines, "poNo")
                        break
            
                    
                    response_msg = "Stock updated successfully"
                        
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