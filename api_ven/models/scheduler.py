from odoo import models, fields, api
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
import datetime as dt
from datetime import datetime
import time
from odoo import http
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import base64
import urllib.request
import re
import hmac
import hashlib
import requests

class SaleOrderExt(models.Model):
    _inherit = "sale.order"

    def get_tokped_order_list_scheduler(self):
        
        # Initialize fs basic information
        # Note: We need to change this variable if there is a changing in
        #       client Tokopedia Data
        fs_id = 17859                

        # =================================================================
        
        # Request access token, expired_date, and token type
        # using function get_tokped_access_token
        access_token, expires_in, token_type = self.get_tokped_access_token()

        # =================================================================

        # Request access token, expired_date, and token type
        # using function get_tokped_access_token
        
        shop_id = self.get_tokped_shop_id(fs_id, access_token, token_type) 
        # shop_id = 3264079
        # =================================================================
        
        # This section will get the datetime from Odoo and convert it into
        # Current Time and 10 minute before (According to the requirement).
        cur_utc = dt.datetime.now(dt.timezone.utc)

        cur_time = cur_utc
        cur_time += dt.timedelta(hours=+7)
        
        ten_m_before = cur_time - dt.timedelta(minutes=10)        

        # ten_m_before = cur_utc
        # ten_m_before += dt.timedelta(hours=-23)
        # raise UserError("Anjay keren nggk") 
        # ten_m_before += dt.timedelta(hours=+6, minutes=-10)
        # ten_m_before += dt.timedelta(hours=-6, minutes=-10)
        # =================================================================
        
        # Prepare the header and params for consume the order list
        
        # The header of the API request
        headers = {
            'Authorization': f'{token_type} {access_token}',
            "Content-Type": "application/json"
        }

        date1 = dt.datetime(2024, 6, 5, 0, 0, tzinfo=dt.timezone.utc)
        date2 = dt.datetime(2024, 6, 7, 0, 0, tzinfo=dt.timezone.utc)
        
        # The params of the API request
        params = {
            'page': 1,
            'per_page': 1000,
            'fs_id': fs_id,
            'from_date': int(ten_m_before.timestamp()),
            'to_date': int(cur_time.timestamp()),
            # 'from_date': int(date1.timestamp()),
            # 'to_date': int(date2.timestamp()),        
            # 'shop_id' : 9075286
            # 'shop_id': shop_id
        }
        
        # # Create API log
        # try:
        #     api_log = request.env['api_ven.api_ven'].create({
        #         'status': 'new',
        #         'created_date': datetime.now(),
        #         'incoming_msg': params,
        #         'message_type': 'FTKPD'
        #     })

        #     api_log['status'] = 'process'
        # except Exception as e:
        #     error['Error'] = str(e)
        #     is_error = True
            
        # # Create the incoming txt
        # try:
        #     api_log['incoming_txt'] = request.env['ir.attachment'].create({
        #         'name': str(api_log['name']) + '_in.txt',
        #         'type': 'binary',
        #         'datas': base64.b64encode(bytes(str(params), 'utf-8')),
        #         'res_model': 'api_ven.api_ven',
        #         'res_id': api_log['id'],
        #         'company_id': self.env.context['allowed_company_ids'][0],
        #         'mimetype': 'text/plain'
        #     })
            
        # except Exception as e:
        #     error['Error'] = str(e)
        #     is_error = True
            
        # Fetch the data for get order list
        resp = requests.get('https://fs.tokopedia.net/v2/order/list', params=params, headers=headers)
        
        # Convert the response data into JSON
        ret = json.loads(resp.content)
        # raise UserError(shop_id)
        # raise UserError(resp.content)
        # ===================================================================
        
        # # This section will record the response if the respon is success or not
        # api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))
        # api_log['response_date'] = datetime.now()
        
        # if resp.status_code == 200:
        #     api_log['status'] = 'success'
        # else:
        #     api_log['status'] = 'error'
            
        # # Create the response txt
        # api_log['response_txt'] = request.env['ir.attachment'].create({
        #     'name': str(api_log['name']) + '_out.txt',
        #     'type': 'binary',
        #     'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
        #     'res_model': 'api_ven.api_ven',
        #     'res_id': api_log['id'],
        #     'company_id': self.env.context['allowed_company_ids'][0],
        #     'mimetype': 'text/plain'
        # })
    
        # ================================================================================
        
        # After we get the data from above section. In this section, we need to
        # consume and re-mapping all the data.
        
        sales_order_list = ret.get("data")        
        sales_order_list_str = json.dumps(sales_order_list, indent=2)
            
        # Raise UserError to display the content of sales_order_list
        # raise UserError(f"Sales Order List: {sales_order_list_str}")        
        
        # Check if there is a new order or not:
        need_updated = False
        
        if sales_order_list != None:
            need_updated = True
            
        # ==============================================================================================
        
        # After checking if there is a new data. If there is a new data, systems
        # will create the new SO

        company_id = self.env.user.company_id.id
        # raise UserError(company_id)
                
        if need_updated:                    
            try:
                for order in sales_order_list:                                        
                    
                    # if order.get("order_status") != 400:
                    #     if order.get("order_status") != 450:
                    #         if order.get("order_status") != 500:
                    #             continue

                    # raise UserError("Test")
                    lines = []
                    buyer_id = ""

                    buyer_information = order.get("buyer")                    
                    buyer_id = buyer_information["id"]

                    # payment_date_str = order.get("payment_date")
                    # payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M:%SZ')
                    # payment_date += dt.timedelta(hours=-7)
                    # ===============================================================================

                    # Create recipient_data

                    recipient_data = order.get("recipient")
                    
                    recipient_name = recipient_data.get("name")
                    recipient_phone = recipient_data.get("phone")

                    recipient_address = recipient_data.get("address")
                    recipient_address_full = recipient_address.get("address_full")
                    recipient_district = recipient_address.get("district")
                    recipient_city = recipient_address.get("city")
                    recipient_province = recipient_address.get("province")
                    recipient_country = recipient_address.get("country")
                    recipient_postal_code = recipient_address.get("postal_code")
                    recipient_geo = recipient_address.get("geo")

                    # ===============================================================================

                    # Create Logistic data
                    logistic_data = order.get("logistics")

                    shipping_agency = logistic_data.get("shipping_agency")
                    service_type = logistic_data.get("service_type")
                    
                    # ===============================================================================

                    # Create amt data
                    amt_data = order.get("amt")

                    shipping_cost = amt_data.get("shipping_cost")
                    insurance_cost = amt_data.get("insurance_cost")
                    
                    total_product_price = amt_data.get("ttl_product_price")

                    total_amount = shipping_cost + insurance_cost + total_product_price

                    # ===============================================================================

                    # Create promo data
                    promo_data = order.get("promo_order_detail")

                    total_cashback = promo_data.get("total_cashback")
                    
                    total_discount_product = promo_data.get("total_discount_product")
                    total_discount_shipping = promo_data.get("total_discount_shipping")
                    total_discount = total_discount_product + total_discount_shipping
                    
                    # ===============================================================================
                    
                    # date_order_converter will use this server time. Which is GMT +14 (if not wrong).
                    # So, we need to convert it as Indonesia (GMT +7) time first.                    
                    date_order_converter = datetime.fromtimestamp(order.get("create_time"))
                    date_order_converter += dt.timedelta(hours=-7)                    
                    
                    # ==============================================================================
                    
                    # This variable will search for the sale order base on invoice_ref_num from TokPed
                    # and compare it with the reference document (origin) in Odoo.
                    sale_order_m = self.env['sale.order'].search([('origin', '=', order.get("invoice_ref_num"))], limit=1)                    

                    # raise UserError(running_code)                    
                    
                    # If there not found the order in list of SO. Systems will create the SO
                    if not sale_order_m:                               
                        
                        # In this logic, we will check if order_status from Tokopedia.
                        # If the order status is 400. Systems will create the sales.order
                        # if the order status is other that 400. Systems will pass it and looking for next list
                        running_code = self.env['ir.sequence'].next_by_code('avi.sales.order')   
                        running_code_str = str(running_code)
                        partner = self.env['res.partner'].search([('name', '=', "TOKOPEDIA CUSTOMER SHIP ADDRESS")], limit=1)                                                       
                        if not partner:                            
                            # Handle the case where the partner does not exist
                            raise ValueError("Partner not found: TOKOPEDIA CUSTOMER SHIP ADDRESS")                        
                        
                        # NOTE if please re-mapping all this mapping:
                        """
                        - Partner Id -> Base on tokopedia customer ID
                        - Company ID -> Must been AVO company ID
                        - partner_invoice_id & partner_shipping_id -> Please checking if this mandatory or not -> mandatory
                        - pricelist_id -> please check if this is mandatory or not -> mandatory: pricelist_id shows the currency used which in Tokopedia's case is IDR
                        - warehouse_id -> please checking if the warehouse already same as the avo needed
                        - partner_invoice_id -> please checking about this mapping (For now, it will be take down)
                        - partner_shipping_id -> please checking about this mapping (For now, it will be take down)
                        """

                        # Define the mapping of shop_id to shop_name
                        shop_id_to_name = {
                            3264079: "omedic",
                            3391175: "3M Littmann Store",
                            5788932: "NVG Indonesia",
                            9075286: "Holicatid",
                            13330723: "VitaHealth Official Store"
                        }
                        
                        # Get the shop_id from the order
                        shop_id = order.get("shop_id")
                        
                        # Get the corresponding shop_name from the mapping
                        shop_name = shop_id_to_name.get(shop_id, "Unknown Shop")  # Default to "Unknown Shop" if shop_id is not found

                        # Get the current date
                        now = datetime.now()
                        
                        # Format the string
                        so_name = f"SO-OR/AVI/{now.year}/{now.month:02}/{now.day:02}/{running_code_str}"
                                            
                        self.env['sale.order'].create({
                            'name': so_name,
                            'x_shop_name': shop_name,
                            'origin': order.get("invoice_ref_num"),
                            'x_studio_doc_trans_code': "OR",
                            'partner_id': partner.id,
                            'partner_invoice_id': partner.id,
                            'partner_shipping_id': partner.id,
                            'company_id': company_id,
                            'date_order': date_order_converter,
                            'picking_policy': "direct",
                            'pricelist_id': 1,
                            'warehouse_id': 17,
                            'x_ecommerce_code': "TKP",
                            'x_buyer_id': buyer_id,
                            'x_shop_id': order.get("shop_id"),
                            # 'x_payment_date': payment_date,
                            'x_recipient_name': recipient_name,
                            'x_recipient_phone': recipient_phone,
                            'x_recipient_full_address': recipient_address_full,
                            'x_recipient_address_district': recipient_district,
                            'x_recipient_address_city': recipient_city,
                            'x_recipient_address_province': recipient_province,
                            'x_recipient_address_country': recipient_country,
                            'x_recipient_address_postal_code': recipient_postal_code,
                            'x_recipient_address_geo': recipient_geo,
                            'x_is_cod_mitra': order.get('is_cod_mitra'),
                            'x_shipping_agency': shipping_agency,
                            'x_service_type': service_type,
                            'x_fulfill_by': order.get("fulfill_by"),
                            'x_shipping_cost': shipping_cost,
                            'x_insurance_cost': insurance_cost,
                            'x_total_product_price': total_product_price,
                            'x_total_discount_product': total_discount_product,
                            'x_total_discount_shipping': total_discount_shipping,
                            'x_total_cashback': total_cashback,
                            'x_order_status': order.get("order_status"),                            
                            'order_line': []
                        })                        
                    else:
                        continue
                    
                    # ===============================================================================
                    # After creating the success create the SO. Order line will created base on the product.
                    
                    # Because we need to get the new sales order (current created sales order). So we will
                    # search it first to get the value.
                    new_sale_order_m = self.env['sale.order'].search([('origin', '=', order.get("invoice_ref_num"))], limit=1)                    

                    if not new_sale_order_m:
                        continue
                    
                    lines = []
                    # ===============================================================================
                    
                    # This section will handle the SO-Line
                    # raise UserError("Odoog")
                    for product in order.get("products"):
                        
                        # Checking if the product existing or not                        
                        is_product = self.env['product.template'].search([('name', '=', product.get("name"))], limit=1)                        
                        
                        # If the product doesn't existing in Odoo. Systems will auto create the product
                        if not is_product:   
                            raise UserError(product.get("name") + " does not exist!")
                            
                            is_product = self.env['product.template'].search([('name', '=', product.get("name"))], limit=1)                            
                            # NOTE if please re-mapping all this mapping:
                            """
                            - categ_id -> Please hardcode this into sale_able product category first
                            - company_id -> Must been AVO company ID
                            - detailed_type -> Please checking if this mandatory or not -> mandatory
                            - pricelist_id -> please check if this is mandatory or not -> not mandatory
                            - warehouse_id -> please checking if the warehouse already same as the avo needed
                            - uom_id -> checking the uom ID is already right or not. You can hardcode it into units
                            """
                            
                            if not is_product:
                                                              
                                self.env['product.template'].create({
                                    'categ_id': 2,
                                    'company_id': company_id,
                                    'detailed_type': "product",
                                    'default_code': product.get("sku"),
                                    'name': product.get("name"),
                                    'purchase_line_warn': "no-message",
                                    'sale_line_warn': "no-message",
                                    'tracking': "none",
                                    'standard_price': product.get("price"),
                                    'uom_id': 1,
                                    'uom_po_id': 1,
                                    'weight': product.get("weight")
                                })                               
                            
                        # After the product created. We will store the product information first using search feature.                                                    
                        product_detail = self.env['product.product'].search([('default_code', '=', product.get("sku"))], limit=1)
                        
                        if not product_detail:                            
                            product_detail = self.env['product.product'].search([('name', '=', product.get("name"))], limit=1) 
                        
                        # This code will make sure there is no error in Odoo creating Product process
                        if not product_detail:
                            raise UserError('Product not found!!')
                        # ===========================================================================
                        
                        # After creating product already existing. We will create the SO Line and all the process is done                        
      #                   new_sale_order_m.order_line.create({
      #                       'company_id': company_id
						# 	'product_id': product_detail.id,
						# 	'name': product.get("name"),
						# 	'order_id': new_sale_order_m.id,
						# 	'product_uom' : product_detail.uom_id.id,
						# 	'product_uom_qty': product.get("quantity"),
      #                       'tax_id': None,
						# 	'price_unit': product.get("price"),
						# 	'display_type': False,
      #                       'x_product_sku': product_detail.default_code,
      #                       'x_product_notes': product.get('notes'),
      #                       'x_is_wholesale': product.get('is_wholesale'),
      #                       'x_stock_status_code': "NM"
						# })              

                        self.env['sale.order.line'].create({
                            'company_id': company_id,
                            'product_id': product_detail.id,
                            'name': product.get("name"),
                            'order_id': new_sale_order_m.id,
                            'product_uom' : product_detail.uom_id.id,
                            'product_uom_qty': product.get("quantity"),
                            'tax_id': [(6, 0, [])] if not product.get("tax_id") else product.get("tax_id"),  # This assumes tax_id should be set as many2many if not None
                            'price_unit': product.get("price"),
                            'display_type': False,
                            'x_product_sku': product_detail.default_code,
                            'x_product_notes': product.get('notes'),
                            'x_is_wholesale': product.get('is_wholesale'),
                            'x_stock_status_code': "NM"
                        })
                        
                        # ===========================================================================

                        # After creating the sales order line. We need to update the price json.
                        # In odoo 14 and 15, It's call as tax_totals_json.                                                                                              
                        # new_amount_total = total_amount - total_discount - total_cashback
                                                
                        # new_sale_order_m.update({
                        #     'amount_total': new_amount_total
                        # })
                        
                        # new_sale_order_m._compute_tax_totals_json()
                        
                        # new_sale_order_m.action_confirm()

                        # raise UserError("Bruh")
                                                
            except Exception as e:
                raise UserError(str(e))