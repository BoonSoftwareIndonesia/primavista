# -*- coding: utf-8 -*-
from odoo import http


# class ProductMove(http.Controller):
#     @http.route('/product_move/product_move', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_move/product_move/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_move.listing', {
#             'root': '/product_move/product_move',
#             'objects': http.request.env['product_move.product_move'].search([]),
#         })

#     @http.route('/product_move/product_move/objects/<model("product_move.product_move"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_move.object', {
#             'object': obj
#         })
