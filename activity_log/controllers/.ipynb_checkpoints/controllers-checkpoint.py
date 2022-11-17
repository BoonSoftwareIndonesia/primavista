# -*- coding: utf-8 -*-
from odoo import http


class ActivityLog(http.Controller):
    @http.route('/activity_log/activity_log', auth='public')
    def index(self, **kw):
        return "Hello, world"

#     @http.route('/activity_log/activity_log/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('activity_log.listing', {
#             'root': '/activity_log/activity_log',
#             'objects': http.request.env['activity_log.activity_log'].search([]),
#         })

#     @http.route('/activity_log/activity_log/objects/<model("activity_log.activity_log"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('activity_log.object', {
#             'object': obj
#         })
