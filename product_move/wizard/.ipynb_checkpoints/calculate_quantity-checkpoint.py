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
        
        for pm in pm_list:
            for trans_code in doc_trans_code:
                pm_test = pm_model.search([('id','=',5120)])
                # raise UserError(str(pm_test))
                
                curr_pml = pml_model.search([('pm', '=', pm.id),('trans_code', '=', trans_code)])
                if curr_pml['id']:
                    continue
                
                from_date = datetime(pm_test.start_date.year, pm_test.start_date.month, 1)
                to_date = pm_test.start_date + relativedelta(months=1)
                to_date = datetime(to_date.year, to_date.month, 1)
                
                domain = [
                    ('product_id', '=', 185),
                    ('picking_id.x_studio_doc_trans_code','=',trans_code),
                    ('location_id', '=', 8),
                    ('date', '>=', from_date),
                    ('date', '<', to_date)
                ]
                res = self.env['stock.move'].search(domain)

                raise UserError((f"{str(res)} from date: {from_date} to date: {to_date}") )
                