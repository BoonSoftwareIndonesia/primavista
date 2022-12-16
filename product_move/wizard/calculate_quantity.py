from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta

class CalculateQuantityWizard(models.TransientModel):
    _name = 'product_move.calculate_quantity.wizard'
    _description = 'Calculate Quantity Wizard'

    def calculate_quantity(self):
        pm_model = self.env['product_move.product_move'] 
        pm_list = pm_model.search([])
        pml_model = self.env['product_move.line'] 
        
        doc_trans_code = ['PODR','GR', '', 'CP', 'OR', 'GRN', 'POR', 'GRA']
        
        # test = []
        for pm in pm_list:
            for trans_code in doc_trans_code:
                qtyIN = 0
                qtyOUT = 0
                # pm_test = pm_model.search([('id','=',13)])
                # pm_test = pm_list
                # pm_test = pm
                # raise UserError(str(pm_test))
                
                curr_pml = pml_model.search([('pm', '=', pm.id),('trans_code', '=', trans_code)])
                if curr_pml['id']:
                    continue
                
                # raise UserError((pm_test.start_date))
                # from_date = datetime(pm_test.start_date.year, pm_test.start_date.month, 1)
                # to_date = pm_test.start_date + relativedelta(months=1)
                # from_date = datetime(2022, 12, 1)
                # to_date = datetime(2023, 1, 1)
                from_date = datetime(pm.start_date.year, pm.start_date.month, 1)
                to_date = pm.start_date + relativedelta(months=1)
                to_date = datetime(to_date.year, to_date.month, 1)
                
                domain = [
                    # ('product_id', '=', 265),
                    ('product_id', '=', pm.product.id),
                    ('picking_id.x_studio_doc_trans_code','=',trans_code),
                    # ('location_id', '=', 8),
                    # ('state', '=', 'Done'),
                    ('date', '>=', from_date),
                    ('date', '<', to_date)
                ]
                res = self.env['stock.move'].search(domain)
                # raise UserError((res.location_id.id))
                for data in res:
                    # test.append(data.quantity_done)
                    if data.location_id.id == 8:
                        qtyIN += data.quantity_done
                    elif data.location_dest_id.id == 8:
                        qtyOUT += data.quantity_done
                    # qtyIN += 1
                
                # raise UserError((qtyOUT))
                pml_model.create({
                    'pm': pm.id,
                    'io_code': "IN",
                    'trans_code': trans_code,
                    'product': res.product_id.id,
                    'quantity': qtyIN
                })
                
                pml_model.create({
                    'pm': pm.id,
                    'io_code': "OUT",
                    'trans_code': trans_code,
                    'product': res.product_id.id,
                    'quantity': qtyOUT
                })
                # raise UserError((f"{str(res)} product: {res.product_id.id} from date: {from_date} to date: {to_date}") )
                # raise UserError((f"{res.id} {res}"))
                # raise UserError((f"{res.location_id.id}"))
                # raise UserError((f"{res.location_id} {res.location_dest_id}"))
                   
              
            
        
             
            
#             qty = 0
                # qty += res.product_uom_qty
                # raise UserError((f"{str(res)} from date: {from_date} to date: {to_date}") )
                # raise UserError((f"{str(res)} product: {pm.product.id} from date: {from_date} to date: {to_date}") )
            
        # raise UserError((f"{str(res)} product: {pm.product.id} from date: {from_date} to date: {to_date}") )
        # raise UserError((str(res)))