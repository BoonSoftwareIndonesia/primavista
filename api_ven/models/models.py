# -*- coding: utf-8 -*-

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
    
# API VEN MODEL ==========================================================================
class api_ven(models.Model):
    _name = 'api_ven.api_ven'
    _description = 'api_ven.api_ven'
    
    # The fields in the api_ven table
    name = fields.Char(string="Message ID", required=True, copy=False, readonly=True, index=True, default=lambda self: ('New'))
    incoming_msg = fields.Text(string="Incoming Message")
    response_msg = fields.Text(string="Response Message")
    status = fields.Selection([('new','New'),('process','Processing'),('success','Success'),('error','Error')])
    created_date = fields.Datetime(string="Created Date")
    response_date = fields.Datetime(string="Response Date")
    message_type = fields.Selection([('RCPT','CRT_RCPT'), ('DO','CRT_DO'), ('PO','DW_PO'), ('SO','DW_SO'), ('PO_RET','DW_PO_RET'), ('SO_RET','DW_SO_RET'), ('RCPT_RET','CRT_RCPT_RET'), ('DO_RET','CRT_DO_RET'), ('CUST','DW_CUST'), ('SHIP','DW_SHIP'), ('PROD','DW_PROD'), ('STOCK','STOCK_COMPARE'), ('ADJUST', 'STOCK_ADJUSTMENT'), ('FTKPD', 'FETCH_TOKOPEDIA'), ('FOL_SHPE', 'FETCH_ORDERLIST_SHOPEE'), ('FSO_SHPE', 'FETCH_SALESORDER_SHOPEE'), ('GET_LOT', 'LOT Adjustment'), ('SAP_PO', 'Send_Odoo_PO_SAP')])
    incoming_txt = fields.Many2one('ir.attachment', string="Incoming txt", readonly=True)
    response_txt = fields.Many2one('ir.attachment', string="Response txt", readonly=True)
    raw_data = fields.Binary(string="Raw Data", attachment=True)
    raw_dataname = fields.Char(string="File Name")
    
    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == ('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('api.seq') or ('New')
        result = super(api_ven, self).create(vals)
        return result

# Override for importing customer and product ======================
class ImportInheritExt(models.TransientModel):
    _inherit = 'base_import.import'

    # For when importing new product or customer
    def execute_import(self, fields, columns, options, dryrun=False):
        # If user clicks import, set the dryrun and test_import context to True so we always test first before importing
        # This is to prevent odoo from sending an api log to wms when the user clicks import and there is an error in the file
        if dryrun == False:
            res = super(ImportInheritExt, self).with_context(test_import=True).execute_import(fields, columns, options, True)
            # If the messages is not [], there is an error, so just return
            # If the message is [], there is no error, so proceed 
            if str(res['messages']) != '[]':
                   return res
        
        if 'test_import' not in self._context:
            # If the context haven't been set, set the context
            res = super(ImportInheritExt, self).with_context(test_import=dryrun).execute_import(fields, columns, options, dryrun)
        else:
            # Else, no need to set the context
            res = super(ImportInheritExt, self).execute_import(fields, columns, options, dryrun)
        return res