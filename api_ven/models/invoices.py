from odoo import models, fields, api
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from lxml import etree

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Adds a new field "Last Updated On"
    x_last_update_time = fields.Datetime(string='Last Updated On', readonly=True, copy=False)

    # These functions would set the last updated on when the user create/modify the account.move model. The custom field above have been applied to Invoices and could be used on other instances that uses the account.move model. You could add said field using Odoo Studio.
    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)
        invoice.update_last_update_time()
        return invoice

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'x_last_update_time' not in vals:
            self.update_last_update_time()
        return res

    def update_last_update_time(self):
        self.x_last_update_time = datetime.now()