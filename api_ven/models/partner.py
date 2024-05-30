from odoo import models, fields, api
import requests
from datetime import datetime
from odoo.http import request, Response
from odoo.exceptions import UserError

class PartnerExt(models.Model):
    _inherit = 'res.partner'
    
    # Override fields ======================
    # Name is required
    name = fields.Char(index=True, required=True)
    # No duplicate x_studio_customer_id
    x_studio_customer_id = fields.Char(string='Customer ID', copy=False, readonly=False)
    # x_studio_customer_group = fields.Char(string='Customer Group',default='IOC')
    x_studio_customer_group = fields.Selection([("APT", "APOTIK"),("CBG", "CABANG"),("CLC","CLC"),("ECO","ECO"),("EVT","EVT"),("HCP","HCP"),("HOS","HOS"), ("INST","INST"), ("IOC","IOC"), ("KAC","KAC"), ("MKT","MKT"), ("MTC","MTC"), ("NA","Not Applicable"), ("PBAK","PBAK"), ("PBF","PBF"), ("PCP","PRINCIPAL"), ("SUPPLIER","Suppliers"), ("SUPPLIERS","SUPPLIERS"), ("TKC","TKC"), ("TKO","TOKO OBAT"), ("TKU","TKU"), ("GHS", "GHS"), ("SLN", "SLN"), ("PHS", "PHS"),],string="Customer Group", default='IOC', allow_null=True) 
    x_owner_name = fields.Selection([
        ('AVI', 'AVI'),
        ('AVIO', 'AVIO'),
        ('BNL', 'BNL'),
        ('ESSILOR', 'ESSILOR'),
        ('OMRON', 'OMRON'),
        ('VITAHEALTH', 'VITAHEALTH'),
        ("OMRON CONS", "OMRON CONS"), 
        ("VITAHEALTH CONS", "VITAHEALTH CONS")
    ], string='Owner')        
    street = fields.Char(default='NA')
    zip = fields.Char(change_default=True, default='12345')
    city = fields.Char(default='NA')    
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]",required=True)
    # Default country Indonesia
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=100)
    
    # # Constraint to check for duplicate x_studio_customer_id ======================
    # @api.constrains('x_studio_customer_id')
    # def _check_x_studio_customer_id(self):
    #     for cust in self:
    #         if cust.x_studio_customer_id:
    #             is_duplicate = False
    #             is_duplicate = request.env['res.partner'].search([
    #                 ('id', '!=', cust.id),
    #                 ('x_studio_customer_id', '=', cust.x_studio_customer_id),
    #                 ('company_id', '=', self.env.context['allowed_company_ids'][0])
    #             ])
    #             if is_duplicate:
    #                 # If duplicate x_studio_customer_id exists, raise user error
    #                 raise UserError(('Duplicate exists: ' + cust.x_studio_customer_id))
    
    
    # # Set copy context if we are duplicating an existing partner ======================
    # @api.returns('self', lambda value: value.id)
    # def copy(self, default=None):
    #     if 'copy_context' not in self._context:
    #         # If copy_context have not been set before
    #         res = super(PartnerExt, self).with_context(copy_context=True).copy(default=default)
    #     else:
    #         # If copy_context have been set before
    #         res = super(PartnerExt, self).copy(default=default)
    #     return res
    
    
    # # Function to set default value if null ======================
    # def set_default(self,partners):
    #     if not partners.x_studio_customer_group:
    #         partners.x_studio_customer_group = "IOC"
    #     if not partners.street:
    #         partners.street = "NA"
    #     if not partners.city:
    #         partners.city = "NA"
    #     if not partners.zip:
    #         partners.zip = "12345"
    #     if not partners.country_id:
    #         partners.country_id = 100
    #     if not partners.company_id:
    #         partners.company_id = self.env.context['allowed_company_ids'][0]
    #     if not partners.x_studio_customer_id:
    #         if partners.type == "delivery" and self.env.context['allowed_company_ids'][0] == 1:
    #             partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('pov.ship.no')
    #         elif partners.type == "delivery" and self.env.context['allowed_company_ids'][0] == 2:
    #             partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('avo.ship.no')
    #         else:
    #             if partners.customer_rank == 1:
    #                 if self.env.context['allowed_company_ids'][0] == 1: 
    #                     partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('pov.customer.id')
    #                 else:
    #                     partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('avo.customer.id')
    #             else:
    #                 if self.env.context['allowed_company_ids'][0] == 1:
    #                     partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('pov.vendor.id')
    #                 else:
    #                     partners.x_studio_customer_id = self.env['ir.sequence'].next_by_code('avo.vendor.id')
    
    # # Triggers the api_dw_customer() function that sends an API log when creating new customer ======================
    # @api.model_create_multi
    # def create(self, vals_list):

    #     # Call the super() method
    #     partners = super(PartnerExt, self).create(vals_list)
        
    #     # Set default values if null
    #     self.set_default(partners)
        
    #     # Get test_import context
    #     test_import = self._context.get('test_import')
        
    #     # If we are not testing (test_import = False), then create customer and send API
    #     if not test_import:
    #         #if we are creating a child partner, create ship_no
    #         if vals_list[0]['type'] == "delivery":

    #             # curr_parent_id = vals_list[0]['parent_id']

    #             # parent_model = request.env['res.partner'].search([('id', '=', curr_parent_id)], limit=1)
                
    #             # if not parent_model:
    #             # raise UserError("Please save customer or vendor first, or contact consultant")
    #         # else:
    #             self.env['res.partner'].api_dw_ship_no(partners)
                
    #             #if not a child partner, Call api_dw_customer to send API to WMS
    #         else:
    #                 # raise UserError("Entry this is a dw_customer")
    #             self.env['res.partner'].api_dw_customer(partners)
            
    #         # Get the new customer's fields and values
    #         new_vals = {}
    #         for rec in partners:
    #             for vals, rec in zip(vals_list, partners):
    #                 new_vals[rec.id] = vals
                    
    #         # Create activity log for customer creation
    #         self.create_activity_logs(partners, "create", new_vals = new_vals)
    #         return partners
    
    
    # # Create activity log ======================
    # def create_activity_logs(self, new_records, method, new_vals = {}, old_vals = {}):
    #     # Assign the activity log model to a variable
    #     activity_log_model = self.env['api_ven.activity_log']
    #     # Get the current model's name (res.partner)
    #     model_model = self.env[self._name]
        
    #     # Get the current user's id
    #     curr_user_id = self._context
    #     curr_user_id = curr_user_id.get('uid')
    #     # Get the current user's name
    #     curr_user_name = self.env['res.users'].browse(curr_user_id)
 
    #     # Declare the values for the activity log's fields
    #     for rec in new_records:
    #         new_activity_log_vals = {
    #             'method': method,
    #             'user':curr_user_id,
    #             'user_name':curr_user_name[0].name,
    #             'model_id': self._name,
    #             'resource_id': rec['id'],
    #             'resource_name': rec['name']
    #         }

    #         # Create activity log
    #         new_log_id = activity_log_model.create(new_activity_log_vals)

    #         # Create the activity log line for the activity log
    #         if method == 'create':
    #             # If we are creating a new partner, call create_log_on_create()
    #             new_log_id[0].create_log_on_create(new_vals[rec['id']], self._name)
    #         elif method == 'write':
    #             # If we are updating an existing partner, call create_log_on_write() 
    #             new_log_id[0].create_log_on_write(new_vals[rec['id']], old_vals[rec['id']],self._name)
    #             pass
    #         else:
    #             # If we are deleting an existing partner, call create_log_on_unlink()
    #             new_log_id[0].create_log_on_unlink(old_vals[rec['id']], self._name)
            
    #     return None
    
    
    # # Triggers the api_dw_customer() function that sends an API log when updating a customer/partner ========
    # def write(self,vals):
    #     # Get the old values before update
    #     old_vals = {
    #             rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())
    #     }
        
    #     # Call the super() method
    #     res = super(PartnerExt, self).write(vals)
        
    #     # If the write_date is not the same as create_date, that means we are doing an update
    #     if self.write_date != self.create_date:
    #         # The result of super() is a bool, so we need to search for the partner to pass to the api function
    #         partners = request.env['res.partner'].search([('id', '=', self.id)], limit=1)

    #         # Get test_import context
    #         test_import = self._context.get('test_import')
            
    #         # Get copy_context context
    #         copy_context = self._context.get('copy_context')
            
    #         # If we are not testing and duplicating, send api
    #         if not test_import and not copy_context:
    #             # Get the new values
    #             new_vals = {rec["id"]: rec for rec in self.with_context(prefetch_fields=False).read(vals.keys())}
                
    #             # Create activity log for partner update
    #             # If want to change password. Please comment below line
    #             self.create_activity_logs(self, "write", new_vals=new_vals, old_vals=old_vals)
                
    #             # Send API to WMS
    #             if partners.type == "delivery":
    #                 if not partners.parent_id: 
    #                     raise UserError("Please save customer or vendor first, or contact consultant")
    #                 else:
    #                     self.env['res.partner'].api_dw_ship_no(partners)
    #             #if not a child partner, Call api_dw_customer to send API to WMS
    #             else:
    #                 # raise UserError("Entry this is a dw_customer")
    #                 self.env['res.partner'].api_dw_customer(partners)
                    
    #     return res
    
    
    # # Override customer/partner deletion to trigger the creation of an activity log when a partner is deleted ======================
    # @api.ondelete(at_uninstall=False)
    # def _unlink_except_user(self):
    #     old_vals = {}
    #     records = []
        
    #     for rec in self:
    #         # Get the values of the partner that will be deleted
    #         old_vals[rec.id] = {
    #             'x_studio_customer_id': "" if not rec.x_studio_customer_id else rec.x_studio_customer_id, 
    #             'name': "" if not rec.name else rec.name, 
    #             'x_studio_customer_group': "" if not rec.x_studio_customer_group else rec.x_studio_customer_group, 
    #             'street': "" if not rec.street else rec.street, 
    #             'city': "" if not rec.city else rec.city, 
    #             'state_id': "" if not rec.state_id.name else rec.state_id.name, 
    #             'zip': "" if not rec.zip else rec.zip, 
    #             'country_id': "" if not rec.country_id.name else rec.country_id.name
    #         }
    #         records.append({'id': rec.id, 'name': rec.name})
        
    #     # Call the super() method
    #     super(PartnerExt, self)._unlink_except_user()
        
    #     # Call create_activity_logs() to trigger the creation of an activity log for partner deletion
    #     self.create_activity_logs(records, "unlink" , old_vals = old_vals)
        
    #     return None    

    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=None):
    #     if args is None:
    #         args = []
            
    #     owner_name = self.env.context.get('owner_name')
    #     if owner_name:
    #         args.append(('x_owner_name', '=', owner_name))        

    #     return super(PartnerExt, self).name_search(name=name, args=args, operator=operator, limit=limit)

    # @api.model
    # def search(self, args=None, offset=0, limit=None, order=None, count=False):
    #     if args is None:
    #         args = []

    #     owner_name = self.env.context.get('owner_name')
    #     if owner_name:
    #         args.append(('x_owner_name', '=', owner_name))        

    #     return super(PartnerExt, self).search(args, offset=offset, limit=limit, order=order, count=count)