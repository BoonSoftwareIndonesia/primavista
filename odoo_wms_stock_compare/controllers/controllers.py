# -*- coding: utf-8 -*-
from odoo import http


class OdooWmsStockCompare(http.Controller):
    @http.route('/odoo_wms_stock_compare/odoo_wms_stock_compare', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/odoo_wms_stock_compare/odoo_wms_stock_compare/objects', auth='public')
    def list(self, **kw):
        return http.request.render('odoo_wms_stock_compare.listing', {
            'root': '/odoo_wms_stock_compare/odoo_wms_stock_compare',
            'objects': http.request.env['odoo_wms_stock_compare.odoo_wms_stock_compare'].search([]),
        })

    @http.route('/odoo_wms_stock_compare/odoo_wms_stock_compare/objects/<model("odoo_wms_stock_compare.odoo_wms_stock_compare"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('odoo_wms_stock_compare.object', {
            'object': obj
        })
