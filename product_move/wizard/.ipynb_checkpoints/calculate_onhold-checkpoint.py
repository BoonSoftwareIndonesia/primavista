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
        pm = self.env['product_move.product_move']
        for product in self.env['product.product'].search([]):
            # prev_month = product['create_date'] + relativedelta(months=-1)
            raise UserError((datetime(2022,1,1) + relativedelta(months=-1) )
            
            # if the pm for the previous month when the product is created has not been created, create the pm
            if pm.search([('start_date','=',prev_month),('product','=',product['id'])]) is False:
                # raise UserError(str(pm.search([('start_date','=',prev_month),('product','=',product['id'])])))
                pm.create({
                    'start_date':prev_month,
                    'product': product['id'],
                    'quantity': 0
                })
                         
            # loop per bulan
            # for dt in rrule.rrule(rrule.MONTHLY, dtstart=product['create_date'], until=now):
                # raise UserError(("hey2"))
                # raise UserError((dt))
                # products.append(dt)
            
            # raise UserError((product['id']))
            # products.append(product)
        # raise UserError((products))