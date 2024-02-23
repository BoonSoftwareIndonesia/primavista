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

"""
Summary Brief:
- This model will control the integration between Odoo and Indonesia E-Commerce like Shopee and Tokopedia.
- For now, the API that working is Tokopedia. But, at 23-02-2024 this API is down due to there is an issue in Tokopedia platform. Latest developer can't rise ticket because we can't access Tokopedia technical ticket trello.
- The Shopee can't be implement due to there is an error in access token. Current Developer (VL) already try to communicated with Shopee team but not get the right answer.
    
Logic:

A. Tokopedia logic:
1. System will request Tokopedia access token using API.
2. This access token will be used to get shop information using API.
3. After we get shop_id using get_shop_information API, system will fetch the order list.
4. After Tokopedia order list already existing, Odoo will process this order list with some case:
==> If Product not exist, Odoo will generate new product
==> After Product exisitng, Odoo will generate the Sales Order and auto confirm it [For additional information. Please re-check the field mapping because in the latest development, developer didn't full considering the field mapping]

B. Shopee Logic:
1. Systems will request the new sign that needed in all API connection. This request will be using API between Shopee and Odoo
2. Shopee will get order_list where this order list only contain order number. [Not like Tokopedia where the order list is include the detail of the order].
3. Each of order in order list, Odoo will request using API request.
4. After Shopee detail order already existing, Odoo will process this order list with some case:
==> If Product not exist, Odoo will generate new product
==> After Product exisitng, Odoo will generate the Sales Order and auto confirm it [For additional information. Please re-check the field mapping because in the latest development, developer didn't full considering the field mapping]
"""


class SaleOrderExt(models.Model):
    _inherit = "sale.order"

    # Compute Total Quantity
    def _compute_x_total_quantity(self):
        for record in self:
            total = 0
            for line in record.order_line:
                total = total + line.product_uom_qty
            
            record['x_studio_total_qty'] = total
    
    # Additional field for sale order
    x_buyer_id = fields.Integer(readonly=False)
    x_ecommerce_code = fields.Char(string='E Commerce Code', readonly=True) 
    x_fulfill_by = fields.Char(string='Fulfill By', readonly=False) 
    x_insurance_cost = fields.Float(string='Insurance Cost', readonly=False) 
    x_is_cod_mitra = fields.Boolean(string='Is Cod Mitra', readonly=False)
    x_order_status = fields.Char(string='Order Status', readonly=False)
    x_payment_date = fields.Datetime(string='Payment Date', readonly=False) 
    x_recipient_address_city = fields.Char(string='Recipient Address City', readonly=False)
    x_recipient_address_country = fields.Char(string='Recipient Address Country', readonly=False)
    x_recipient_address_district = fields.Char(string='Recipient Address District', readonly=False)
    x_recipient_address_geo = fields.Char(string='Recipient Address Geo', readonly=False)
    x_recipient_address_postal_code = fields.Char(string='Recipient Address Postal Code', readonly=False)
    x_recipient_address_province = fields.Char(string='Recipient Address Province', readonly=False)
    x_recipient_full_address = fields.Char(string='Recipient Full Address', readonly=False)
    x_recipient_name = fields.Char(string='Recipient Name', readonly=False)
    x_recipient_phone = fields.Char(string='Recipient Phone', readonly=False)
    x_service_type = fields.Char(string='Service Type', readonly=False)
    x_shipping_agency = fields.Char(string='Shipping Agency', readonly=False)
    
    x_shipping_cost = fields.Float(string='Shipping Cost', readonly=False)
    x_shop_id = fields.Integer(readonly=False)
    x_studio_total_qty = fields.Float(string='Total Quantity', readonly=True, compute='_compute_x_total_quantity')
    x_total_discount_product = fields.Float(string='Total Discount Product', readonly=False)
    x_total_discount_shipping = fields.Float(string='Total Discount Shipping', readonly=False)
    x_total_product_price = fields.Float(string='Total Product Price', readonly=False)
    x_total_cashback = fields.Float(string='Total Cashback', readonly=False)


class SaleOrderLineExt(models.Model):
    _inherit = "sale.order.line"

    # Additional field for sale order line
    x_product_sku = fields.Char(string = "Product SKU", readonly=False)
    x_product_notes = fields.Char(string = "Product Note", readonly=False)
    x_is_wholesale = fields.Boolean(string='Wholesale', readonly=False)

    # Additional, since in product already product SKU (Internal Reference). In the next development, you can considering to use the product internal reference.

# Fetch Data From TokPed =============================================================
class ApiFetchTokPed(models.Model):
    _inherit = "sale.order"

    def get_tokped_access_token(self):
        """
        This function has a purpose to Request tokopedia access token,
        token type, and expired date. After that, load it as a variable
        """
        # =================================================================
        
        # Initialize Client basic information
        # Note: We need to change this variable if there is a changing in
        #       client Tokopedia Data
        client_id = "718e4748bb0d44c28f50b4da4d131d69"
        client_secret = "18e291fcb7104c508ac80d3e1dfd20d1"
        
        # =================================================================
        
        # Encode the client id + client server and create it
        # as auth key
        key_message = client_id + ":" + client_secret
        key_bytes = key_message.encode('ascii')
        
        base64_bytes = base64.b64encode(key_bytes)
        auth_key = base64_bytes.decode("ascii")

        # =================================================================

        # Create the header for fetch Access token API
        headers = {
            'Authorization': 'Basic ' + auth_key,
            'User-Agent': 'PostmanRuntime/7.17.1',
        }

        # Create Params for fetch Access token API
        params = {
            'grant_type': 'client_credentials',
        }

        # Create request and get the data
        resp = requests.post('https://accounts.tokopedia.com/token', params=params, headers=headers)

        if resp.status_code != 200:
            raise UserError(f"Error when get generate access token from Tokopedia. Please contact your Boonsoftware consultant for more information!")

        # Convert the return result from token API to JSON
        ret = json.loads(resp.content)

        # =================================================================

        # Store access token, Expires_date, and token_type
        access_token = ret.get("access_token")
        expires_in = ret.get("expires_in")
        token_type = ret.get("token_type")

        # =================================================================

        return access_token, expires_in, token_type

    def get_tokped_shop_id(self, fs_id, access_token, token_type):
        """
        This section has a purpose to fetch Shop Information from TokPed
        and return shopId
        """

        # =================================================================
        
        # Prepare the requirement to fetch Shop List API
        headers = {
            'Authorization': f'{token_type} {access_token}',
        }

        params = {
            'fs_id': fs_id,
            'page': 1,
            'per_page': 1
        }

        # Create request and get the shop list      
        resp = requests.get(f'https://fs.tokopedia.net/v1/shop/fs/{fs_id}/shop-info', headers=headers, params=params)

        if resp.status_code != 200:
            raise UserError(f"Error when get shop information from TokPed. Please contact your Boonsoftware consultant for more information!")
        
        # Convert the return result from token API to JSON
        ret = json.loads(resp.content)

        # =================================================================

        # In here we need to prepare the shop list into the shop detail info        
        # so we can get the shop ID
        shop_list = ret.get("data")
        
        shop_detail_info = shop_list[0]
        
        shop_id = shop_detail_info.get("shop_id")

        # =================================================================

        return shop_id
    
    def get_tokped_order_list(self):

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
        # =================================================================
        
        # This section will get the datetime from Odoo and convert it into
        # Current Time and 10 minute before (According to the requirement).
        cur_utc = dt.datetime.now(dt.timezone.utc)

        cur_time = cur_utc
        cur_time += dt.timedelta(hours=+7)

        ten_m_before = cur_utc
        ten_m_before += dt.timedelta(hours=-23)
        # ten_m_before += dt.timedelta(hours=+6, minutes=-10)
        # ten_m_before += dt.timedelta(hours=-6, minutes=-10)
        # =================================================================
        
        # Prepare the header and params for consume the order list
        
        # The header of the API request
        headers = {
            'Authorization': f'{token_type} {access_token}',
            "Content-Type": "application/json"
        }
        
        # The params of the API request
        params = {
            'page': 1,
            'per_page': 1000,
            'fs_id': fs_id,
            'from_date': int(ten_m_before.timestamp()),
            'to_date': int(cur_time.timestamp()),
            'shop_id': shop_id
        }
        
        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': params,
                'message_type': 'FTKPD'
            })

            api_log['status'] = 'process'
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
            
        # Create the incoming txt
        try:
            api_log['incoming_txt'] = request.env['ir.attachment'].create({
                'name': str(api_log['name']) + '_in.txt',
                'type': 'binary',
                'datas': base64.b64encode(bytes(str(params), 'utf-8')),
                'res_model': 'api_ven.api_ven',
                'res_id': api_log['id'],
                'company_id': self.env.context['allowed_company_ids'][0],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
            
        # Fetch the data for get order list
        resp = requests.get('https://fs.tokopedia.net/v2/order/list', params=params, headers=headers)
        
        # Convert the response data into JSON
        ret = json.loads(resp.content)
        # ===================================================================
        
        # This section will record the response if the respon is success or not
        api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        if resp.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'
            
        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })
    
        # ================================================================================
        
        # After we get the data from above section. In this section, we need to
        # consume and re-mapping all the data.
        
        sales_order_list = ret.get("data")
        
        # Check if there is a new order or not:
        need_updated = False
        
        if sales_order_list != None:
            need_updated = True
            
        # ==============================================================================================
        
        # After checking if there is a new data. If there is a new data, systems
        # will create the new SO
        if need_updated:
            try:
                for order in sales_order_list:

                    if order.get("order_status") != 400:
                        if order.get("order_status") != 450:
                            if order.get("order_status") != 500:
                                continue
                    
                    lines = []
                    buyer_id = ""

                    buyer_information = order.get("buyer")
                    buyer_id = buyer_information["id"]

                    payment_date_str = order.get("payment_date")
                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M:%SZ')
                    payment_date += dt.timedelta(hours=-7)
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
                    sale_order_m = request.env['sale.order'].search([('origin', '=', order.get("invoice_ref_num"))], limit=1)

                    # raise UserError(running_code)
                    
                    # If there not found the order in list of SO. Systems will create the SO
                    if not sale_order_m:

                        # In this logic, we will check if order_status from Tokopedia.
                        # If the order status is 400. Systems will create the sales.order
                        # if the order status is other that 400. Systems will pass it and looking for next list
                        running_code = self.env['ir.sequence'].next_by_code('avo.sale.order')


                        # NOTE if please re-mapping all this mapping:
                        """
                        - Partner Id -> Base on tokopedia customer ID
                        - Company ID -> Must been AVO company ID
                        - partner_invoice_id & partner_shipping_id -> Please checking if this mandatory or not
                        - pricelist_id -> please check if this is mandatory or not
                        - warehouse_id -> please checking if the warehouse already same as the avo needed
                        - 
                        """
                            
                        request.env['sale.order'].create({
                            'name': running_code,
                            'origin': order.get("invoice_ref_num"),
                            'x_studio_doc_trans_code': "OR",
                            'partner_id': 1043,
                            'company_id': 2,
                            'date_order': date_order_converter,
                            'partner_invoice_id': 836,
                            'partner_shipping_id': 836,
                            'picking_policy': "direct",
                            'pricelist_id': 1,
                            'warehouse_id': 2,
                            'x_ecommerce_code': "TKP",
                            'x_buyer_id': buyer_id,
                            'x_shop_id': order.get("shop_id"),
                            'x_payment_date': payment_date,
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
                    new_sale_order_m = request.env['sale.order'].search([('origin', '=', order.get("invoice_ref_num"))], limit=1)

                    if not new_sale_order_m:
                        continue
                    
                    lines = []
                    # ===============================================================================
                    
                    # This section will handle the SO-Line
                    for product in order.get("products"):
                        
                        # Checking if the product existing or not
                        is_product = request.env['product.template'].search([('default_code', '=', product.get("sku"))], limit=1)
                        
                        # If the product doesn't existing in Odoo. Systems will auto create the product
                        if not is_product:

                            is_product = request.env['product.template'].search([('name', '=', product.get("name"))], limit=1)
                            # NOTE if please re-mapping all this mapping:
                            """
                            - categ_id -> Please hardcode this into sale_able product category first
                            - company_id -> Must been AVO company ID
                            - detailed_type -> Please checking if this mandatory or not
                            - pricelist_id -> please check if this is mandatory or not
                            - warehouse_id -> please checking if the warehouse already same as the avo needed
                            - uom_id -> checking the uom ID is already right or not. You can hardcode it into units
                            """
                            
                            if not is_product:
                                request.env['product.template'].create({
                                    'categ_id': 1,
                                    'company_id': 2,
                                    'detailed_type': "product",
                                    'default_code': product.get("sku"),
                                    'name': product.get("name"),
                                    'purchase_line_warn': "no-message",
                                    'sale_line_warn': "no-message",
                                    'tracking':"none",
                                    'standard_price': product.get("price"),
                                    'uom_id' : 1,
                                    'uom_po_id': 1,
                                    'weight': product.get("weight")
                                })
                            
                        # =========================================================================================================
                        
                        # After the product created. We will store the product information first using search feature.
                        product_detail = request.env['product.product'].search([('default_code', '=', product.get("sku"))], limit=1)

                        if not product_detail:
                            product_detail = request.env['product.product'].search([('name', '=', product.get("name"))], limit=1) 
                        
                        # This code will make sure there is no error in Odoo creating Product process
                        if not product_detail:
                            raise UserError('Product not found!!')
                        # ===========================================================================
                        
                        # After creating product already existing. We will create the SO Line and all the process is done
                        new_sale_order_m.order_line.create({
							'product_id': product_detail.id,
							'name': product.get("name"),
							'order_id': new_sale_order_m.id,
							'product_uom' : product_detail.uom_id.id,
							'product_uom_qty': product.get("quantity"),
                            'tax_id': None,
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
                        
                        new_amount_total = total_amount - total_discount - total_cashback
                        
                        new_sale_order_m.update({
                            'amount_total': new_amount_total
                        })

                        new_sale_order_m._compute_tax_totals_json()

                        new_sale_order_m.action_confirm()
                        
            except Exception as e:
                raise UserError(str(e))



# Fetch Data From Shopee =============================================================
class ApiFetchShopee(models.Model):
    _inherit = "sale.order"

    def generate_shopee_sign(self, partner_id, path, timespam, access_token, shop_id):
        tmp = "6f767666617044757861436d6a776e556f51595056624e61526c595667785059"
    
        partner_key = tmp.encode()
        
        tmp_base_string = f"{partner_id}{path}{timespam}{access_token}{shop_id}"
        
        base_string = tmp_base_string.encode()
        
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        
        return sign
    
    def get_shopee_order_list(self):
        # ======================================================================
        # Basic information
        host = "https://partner.test-stable.shopeemobile.com"
        partner_id = 1036815
        tmp = "6f767666617044757861436d6a776e556f51595056624e61526c595667785059"
        
        # Shop information
        shop_id = 89935
        
        # Basic authentication
        code = "4677547467766269556468564d6c5468"
        access_token = "564948784462685872694b786a6b6353"
        refresh_token = "42466e6d485572795559474d4149506b"
        # =================================================================

        # This section has a purpose to fetch order list information from Shopee

        # Prepare the requirement to fetch order List API
        headers = {
            'Authorization': f'{access_token}',
        }

        timespam = time.time()

        path = "/api/v2/order/get_order_list"
    
        sign = self.generate_shopee_sign(partner_id, path, timespam, access_token, shop_id)
    
        cur_utc = dt.datetime.now(dt.timezone.utc)
    
        cur_time = cur_utc
        cur_time += dt.timedelta(hours=+7)
        ts_cur_time = datetime.timestamp(cur_time)
    
        before_time = cur_utc
        before_time += dt.timedelta(hours=-23)
        ts_time_from = datetime.timestamp(before_time)
        # =================================================================

        # Prepare the header and params for consume the order list

        # The header of the API request
        headers = {
            'Authorization': f'{access_token}',
            "Content-Type": "application/json"
        }
    
        params = {
            'access_token': access_token,
            'cursor': '""',
            # 'order_status': 'COMPLETED', ==> if we want to spesific it. Use this field.
            'page_size': 20,
            'partner_id': partner_id,
            'request_order_status_pending': 'true',
            'response_optional_fields': 'order_status',
            'cursor': "",
            'shop_id': shop_id,
            'sign': sign,
            'time_from': int(ts_time_from),
            'time_to': int(ts_cur_time),
            'time_range_field': 'create_time',
            'timestamp': timespam,
        }

        # Create API log
        try:
            api_log = request.env['api_ven.api_ven'].create({
                'status': 'new',
                'created_date': datetime.now(),
                'incoming_msg': params,
                'message_type': 'FOL_SHPE'
            })

            api_log['status'] = 'process'
        except Exception as e:
            error['Error'] = str(e)
            is_error = True

        # Create the incoming txt
        try:
            api_log['incoming_txt'] = request.env['ir.attachment'].create({
                'name': str(api_log['name']) + '_in.txt',
                'type': 'binary',
                'datas': base64.b64encode(bytes(str(params), 'utf-8')),
                'res_model': 'api_ven.api_ven',
                'res_id': api_log['id'],
                'company_id': self.env.context['allowed_company_ids'][0],
                'mimetype': 'text/plain'
            })
        except Exception as e:
            error['Error'] = str(e)
            is_error = True
    
        full_url = host + path

        # Fetch the data for get order list
        resp = requests.get(
            full_url,
            params=params
        )

        # Convert the response data into JSON
        ret = json.loads(resp.content)

        
        # ===================================================================

        # This section will record the response if the respon is success or not
        api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))
        api_log['response_date'] = datetime.now()
        
        if resp.status_code == 200:
            api_log['status'] = 'success'
        else:
            api_log['status'] = 'error'

        # Create the response txt
        api_log['response_txt'] = request.env['ir.attachment'].create({
            'name': str(api_log['name']) + '_out.txt',
            'type': 'binary',
            'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
            'res_model': 'api_ven.api_ven',
            'res_id': api_log['id'],
            'company_id': self.env.context['allowed_company_ids'][0],
            'mimetype': 'text/plain'
        })
        
        # ===================================================================
        # In this section, systems will check if there is a new order or not.

        need_updated = False
        # Get Shopee response and spesific get order_list
        sales_order_list = ret.get("response").get("order_list")

        # Checking if the sales_order_list is existing or not
        if sales_order_list != None:
            need_updated = True

        # ===================================================================
        
        # After checking if there is a new data. If there is a new data, systems
        # will create the new SO
        if need_updated:
            try:
                for order in sales_order_list:
                    # ====================================================================
                    # Checking the order
                    
                    # Checking if the order status same as the requirement
                    if order.get("order_status") != "READY_TO_SHIP":
                        if order.get("order_status") != "PROCESSED":
                            if order.get("order_status") != "SHIPPED":
                                continue

                    # This variable will search for the sale order base on invoice_ref_num from TokPed
                    # and compare it with the reference document (origin) in Odoo.
                    existing_order = request.env['sale.order'].search([('origin', '=', order.get("order_sn"))], limit=1)

                    if existing_order:
                        continue

                    # ====================================================================
                    # If all the validate pass, we can make sure there is a new order

                    new_path = "/api/v2/order/get_order_detail"
                    new_timestamp = time.time()
                    new_sign = self.generate_shopee_sign(partner_id, new_path, new_timestamp, access_token, shop_id)

                    # =======================================================================

                    params = {
                        'access_token': access_token,
                        'order_sn_list': f"[{order.get('order_sn')}]",
                        'partner_id': partner_id,
                        'request_order_status_pending': 'true',
                        'response_optional_fields': '["buyer_user_id,buyer_username,estimated_shipping_fee"]',
                        'shop_id': shop_id,
                        'sign': new_sign,
                        'timestamp': new_timestamp,
                    }

                    # Create API log
                    try:
                        api_log = request.env['api_ven.api_ven'].create({
                            'status': 'new',
                            'created_date': datetime.now(),
                            'incoming_msg': params,
                            'message_type': 'FSO_SHPE'
                        })
            
                        api_log['status'] = 'process'
                    except Exception as e:
                        error['Error'] = str(e)
                        is_error = True
            
                    # Create the incoming txt
                    try:
                        api_log['incoming_txt'] = request.env['ir.attachment'].create({
                            'name': str(api_log['name']) + '_in.txt',
                            'type': 'binary',
                            'datas': base64.b64encode(bytes(str(params), 'utf-8')),
                            'res_model': 'api_ven.api_ven',
                            'res_id': api_log['id'],
                            'company_id': self.env.context['allowed_company_ids'][0],
                            'mimetype': 'text/plain'
                        })
                    except Exception as e:
                        error['Error'] = str(e)
                        is_error = True

                    full_url = host + new_path

                    resp = requests.get(
                        full_url,
                        params=params
                    )
                    
                    ret = json.loads(resp.content)

                    # ===================================================================

                    # This section will record the response if the respon is success or not
                    api_log['response_msg'] = base64.b64encode(bytes(str(resp.text), 'utf-8'))
                    api_log['response_date'] = datetime.now()
                    
                    if resp.status_code == 200:
                        api_log['status'] = 'success'
                    else:
                        api_log['status'] = 'error'
            
                    # Create the response txt
                    api_log['response_txt'] = request.env['ir.attachment'].create({
                        'name': str(api_log['name']) + '_out.txt',
                        'type': 'binary',
                        'datas': base64.b64encode(bytes(str(resp.text), 'utf-8')),
                        'res_model': 'api_ven.api_ven',
                        'res_id': api_log['id'],
                        'company_id': self.env.context['allowed_company_ids'][0],
                        'mimetype': 'text/plain'
                    })
                    
                    # ===================================================================
                    
            except Exception as e:
                raise UserError(str(e))