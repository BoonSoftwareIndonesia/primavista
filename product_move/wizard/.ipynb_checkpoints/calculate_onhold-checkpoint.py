from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta

class CalculateOnholdWizard(models.TransientModel):
    _name = 'product_move.calculate_onhold.wizard'
    _description = 'Calculate Onhold Quantity Wizard'

    def calculate_onhold(self):
        products = []
        now = datetime(2022,12,1)
        pm_model = self.env['product_move.product_move']
        products = self.env['product.product'].search([])
        
        for product in products:
            curr_month = datetime(product['create_date'].year, product['create_date'].month, 1)
            self._calculate_onhold_past(product, curr_month, pm_model)
            
            
    def _calculate_onhold_prev_month(self, product, curr_month ,pm_model):
        prev_month = curr_month + relativedelta(months=-1)
        pm_product = pm_model.search([('start_date','=',prev_month),('product','=',product['id'])])
        
        # if the pm for the previous month when the product is created has not been created, create the pm
        if pm_product['id'] is False:
            try:
                pm_model.create({
                    'start_date':prev_month,
                    'product': product['id'],
                    'quantity': 0
                })
            except e:
                raise UserError(str(e))
                
    def _calculate_onhold_past(self, product, curr_month, pm_model):
        until_date = datetime.now()
        until_date = datetime(until_date.year, until_date.month, 1) 

        # loop per bulan
        for dt in rrule.rrule(rrule.MONTHLY, dtstart=curr_month, until=until_date):
            pm_product = pm_model.search([('start_date','=',dt),('product','=',product['id'])])
            
            if pm_product['id'] is False:
                try:
                    pm_model.create({
                        'start_date': dt,
                        'product': product.id,
                        'quantity': product.with_context({'to_date': dt}).qty_available,
                        'value': product.standard_price * product.with_context({'to_date': dt}).qty_available
                    })
                except Exception as e:
                    raise UserError(str(e))
                