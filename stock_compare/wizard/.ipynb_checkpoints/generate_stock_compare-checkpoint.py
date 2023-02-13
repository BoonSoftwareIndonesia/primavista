from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta

class CalculateOnholdWizard(models.TransientModel):
    _name = 'stock_compare.generate_stock_compare.wizard'
    _description = 'Generate Stock Compare Report'

    def generate_stock_compare(self):
       # raise UserError("hey")
        return