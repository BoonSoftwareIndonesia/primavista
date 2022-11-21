import re
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class CalendarEventExt(models.Model):
    _inherit = 'calendar.event'
    x_studio_latitude = fields.Float('Location Latitude', compute = '_compute_lat_long')
    x_studio_longitude = fields.Float('Location Longitude', compute = '_compute_lat_long')
    x_studio_check_status = fields.Boolean('Check in status of the meeting', default = False, copy = False)
    
    @api.model
    def checking_in(self, eventId):
#         Changing calendar event check status to True
        curr_pick = request.env['calendar.event'].search([('id', '=', int(eventId))], limit=1)
        curr_pick.update({'x_studio_check_status': True})
        return True
    
    @api.model
    def get_check_status(self, eventId):
#         Getting check status of the calendar event
        curr_pick = request.env['calendar.event'].search([('id', '=', int(eventId))], limit=1)
        return curr_pick.x_studio_check_status
    
    @api.model
    def send_notification(self, val_list=None):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': val_list[0],
                'message': val_list[1],
                'sticky': True,
            }
        }
        return notification
    
    @api.model
    def action_test(self, val_list=None):
        x = requests.get('https://w3schools.com')
        curr_loc = self.location
        
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': val_list[0],
                'message': val_list[1],
                'sticky': True,
            }
        }
        return notification
#         APIKey = 'AIzaSyBH4JCdioG8uH8HVtHJLwucbbiHxtRNMPE'
#         base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
#         endpoint = f"{base_url}?address={curr_loc}&key={APIKey}"
#         r = requests.get(endpoint)
#         if r.status_code not in range(200,299):
#             return None,None
# #         try:
#         results = r.json()['results'][0]
#         lat = results['geometry']['location']['lat']
#         lng = results['geometry']['location']['lng']
#         except:
#             pass
#         return lat, lng
    
    @api.depends('location')
    def _compute_lat_long(self):
#         Setting lat and long from the record location
#         Accessing google API not implemented
        for rec in self:
            if rec.location == 'Online' or not rec.location:
#                 If there is no location or the location is online, the lat and long will be 0, 0
                rec.x_studio_latitude = None
                rec.x_studio_longitude = None
            elif rec.location:
#                 Should be changed with the long and lat from google API
                rec.x_studio_latitude = 20
                rec.x_studio_longitude = 10