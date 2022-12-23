from odoo import models, fields, api
from odoo.exceptions import UserError
import os
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta
import base64
import zipfile

class CalculateQuantityWizard(models.TransientModel):
    _name = 'product_move.calculate_quantity.wizard'
    _description = 'Calculate Quantity Wizard'
    contract_template = fields.Binary('Template', compute="_get_template")
    contract_template_name = fields.Char('Template Name', compute="_get_template_name")
    
    def calculate_quantity(self):
        pm_model = self.env['product_move.product_move'] 
        pm_list = pm_model.search([])
        pml_model = self.env['product_move.line'] 
        
        doc_trans_code = ['PODR','GR', '', 'CP', 'OR', 'GRN', 'POR', 'GRA']
        
        test = []
        
        # test2 = 0
        for pm in pm_list:
            for trans_code in doc_trans_code:
                qtyIN = 0
                qtyOUT = 0
                
                curr_pml = pml_model.search([('pm', '=', pm.id),('trans_code', '=', trans_code)])
                if curr_pml['id']:
                    continue
                
                from_date = datetime(pm.start_date.year, pm.start_date.month, 1)
                to_date = pm.start_date + relativedelta(months=1)
                to_date = datetime(to_date.year, to_date.month, 1)
                
                domain = [
                    # ('product_id', '=', 265),
                    ('product_id', '=', pm.product.id),
                    ('picking_id.x_studio_doc_trans_code','=',trans_code),
                    # ('location_id', '=', 8),
                    # ('state', '=', 'done'),
                    ('date', '>=', from_date),
                    ('date', '<', to_date)
                ]
                res = self.env['stock.move'].search(domain)
                
                sm_val_in = 0
                sm_val_out = 0

                for data in res:
                    if data.location_id.id == 8:
                        qtyOUT+=data.quantity_done
                        sm_val_out += data.stock_valuation_layer_ids.value
                    elif data.location_dest_id.id == 8:
                        qtyIN+=data.quantity_done
                        sm_val_in += data.stock_valuation_layer_ids.value
                
                pml_model.create({
                    'pm': pm.id,
                    'io_code': "IN",
                    'trans_code': trans_code,
                    'product': pm.product.id,
                    'quantity': qtyIN,
                    'value': sm_val_in
                })
                
                pml_model.create({
                    'pm': pm.id,
                    'io_code': "OUT",
                    'trans_code': trans_code,
                    'product': pm.product.id,
                    'quantity': qtyOUT,
                    'value':sm_val_out
                })
        
    def testing_func(self):
        domain = [
                ('product_id', '=', 265),
                # ('product_id', '=', pm.product.id),
                ('picking_id.x_studio_doc_trans_code','=','PODR'),
            ]
        
        all_values = []
        
        res = self.env['stock.move'].search(domain)
        sm_val_out = 0
        sm_val_in = 0
        total_val = 0
        
        for sm in res:
            if sm.location_id.id == 8:
                sm_val_out += sm.stock_valuation_layer_ids.value
            else:
                sm_val_in += sm.stock_valuation_layer_ids.value
                
            new_dict = {sm.id: (sm.stock_valuation_layer_ids.value, sm.location_id.id)}
            all_values.append(new_dict)
        
        total_val = sm_val_in + sm_val_out
            
        raise UserError((f"Total val: {total_val}\nVal in: {sm_val_in} - Val out: {sm_val_out}\n{all_values}"))

    def calculate_quantity_2(self):
        pm_model = self.env['product_move.product_move'] 
        pm_list = pm_model.search(["|",('product', '=', 265), ('product', '=', 185)])

        doc_trans_code = ['PODR','GR', '', 'CP', 'OR', 'GRN', 'POR', 'GRA']
        all_res = {}
        
        for pm in pm_list:
            from_date = datetime(pm.start_date.year, pm.start_date.month, 1)
            to_date = pm.start_date + relativedelta(months=1)
            to_date = datetime(to_date.year, to_date.month, 1)
            
            new_dict = {
                "IN":{
                    "OR": 0,
                    "POR":0,
                    "PODR":0,
                    "GR": 0,
                    "GRN": 0,
                    "GRA": 0,
                    "CP": 0,
                    "Undefined":0 
                },
                "OUT":{
                    "OR": 0,
                    "POR":0,
                    "PODR":0,
                    "GR": 0,
                    "GRN": 0,
                    "GRA": 0,
                    "CP": 0,
                    "Undefined":0
                }
            }

            domain = [
                ('product_id', '=', pm.product.id),
                ('state', '=', 'done'),
                ('date', '>=', from_date),
                ('date', '<', to_date)
            ]

            res = self.env['stock.move'].search(domain)
            
            if len(res) == 0:
                date_str = from_date.strftime("%m/%d/%Y")
                if pm.product.id not in all_res:
                    all_res[pm.product.id] = {date_str:new_dict}
                all_res[pm.product.id][date_str] = new_dict
                all_res[pm.product.id][date_str]["start_quantity"] = pm.quantity
                continue
            
            quan_test = []
            loc_test = []

            for sm in res:
                if sm.location_id.id == 8:
                    quan_test.append(sm.quantity_done * -1)
                    
                    if sm.picking_id.x_studio_doc_trans_code:
                        new_dict["OUT"][sm.picking_id.x_studio_doc_trans_code] += sm.quantity_done
                    else:
                        new_dict["OUT"]["Undefined"] += sm.quantity_done
                else:
                    quan_test.append(sm.quantity_done)

                    if sm.picking_id.x_studio_doc_trans_code:
                        new_dict["IN"][sm.picking_id.x_studio_doc_trans_code] += sm.quantity_done
                    else:
                        new_dict["IN"]["Undefined"] += sm.quantity_done
                
                loc_test.append(sm.location_id)
            
            date_str = from_date.strftime("%m/%d/%Y")
            if pm.product.id not in all_res:
                all_res[pm.product.id] = {date_str:new_dict}
            all_res[pm.product.id][date_str] = new_dict
            all_res[pm.product.id][date_str]["start_quantity"] = pm.quantity
            # raise UserError((f"{from_date} - {to_date}: {quan_test} - {sm.location_id} \n {new_dict}"))
            
            self.convert_to_excel()
           
        # raise UserError(str(all_res))

    def convert_to_excel(self):
        self.contract_template = base64.b64encode(str.encode("AAAAAAAAAAAAAAAAAAA"))
        self.contract_template_name = "nnn.txt"
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url': f'/web/content/product_move.calculate_quantity.wizard/{self.id}/contract_template/nnn.txt?download=true',
            'target':'self'
        }
    
    def _get_template(self):
        self.contract_template = base64.b64encode(open("/home/odoo/src/user/product_move/static/src/xlsx/nnn.txt", "rb").read())
    
    def _get_template_name(self):
        self.contract_template_name = "nnn.txt"
    
    def get_contract_template(self):
        zip_archive = zipfile.ZipFile("/home/odoo/src/user/product_move/static/src/xlsx/test.rar", "w")
        self.contract_template = base64.b64encode(open("/home/odoo/src/user/product_move/static/src/xlsx/nnn.txt", "rb").read())
        self.contract_template_name = "nnn.txt"
        
        return {
                'type': 'ir.actions.act_url',
                'url': str('/home/odoo/src/user/product_move/static/src/xlsx/')+str("test.rar"),
                'target': 'new',
        }
        # return {
        #     'type': 'ir.actions.act_url',
        #     'name': 'contract',
        #     'url': f'/web/content/product_move.calculate_quantity.wizard/{self.id}/contract_template/nnn.txt?download=true',
        #     'target':'self'
        # }
                