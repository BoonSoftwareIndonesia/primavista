from odoo import models, fields, api
# from openerp.osv import osv
from odoo.http import request, Response
import json, datetime, requests, base64, unicodedata
import datetime as dt
from datetime import datetime
from odoo import http
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import base64
import urllib.request
import re

"""
    Summary Brief:
    - This is an overide create for calling the running number for POV and AVO
    - Since there are only 2 Owner Code (WMS) == Company (Odoo). So there is only 2 running number

    LOGIC:
    1.   In Create logic, we will checking the active company.

    NOTE:
    - Please MAKE SURE THE SEQUENCE NUMBER ALREADY EXIST FIRST
"""



class CreatePORunningNumber(models.Model):
    _inherit = ['purchase.order']

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        # Ensures default picking type and currency are taken from the right company.
        self_comp = self.with_company(company_id)
        if vals.get('name', 'New') == 'New':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if self.env.context['allowed_company_ids'][0] == 1: 
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('pov.purchase.order', sequence_date=seq_date) or '/'
            else:
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('avo.purchase.order', sequence_date=seq_date) or '/'
            
        vals, partner_vals = self._write_partner_values(vals)
        res = super(CreatePORunningNumber, self_comp).create(vals)
        if partner_vals:
            res.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return res


class CreateSORunningNumber(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', 'New') == 'New':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if self.env.context['allowed_company_ids'][0] == 1: 
                vals['name'] = self.env['ir.sequence'].next_by_code('pov.sale.order', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('avo.sale.order', sequence_date=seq_date) or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist.id)
        result = super(CreateSORunningNumber, self).create(vals)
        return result