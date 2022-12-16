# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.record3'
    _description = 'Record Report3'
    _auto = False

    id = fields.Integer(string="Id",readonly=True)
    start_date = fields.Datetime(string="Start Date",readonly=True)
    io_code = fields.Char(string="IO Code",readonly=True)
    product = fields.Many2one('product.product', string="Product",readonly=True)
    trans_code = fields.Char(string="Trans Code",readonly=True)
    start_quantity = fields.Float(string="Start Quantity",readonly=True)
    quantity = fields.Float(string="Quantity",readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'product_move_record3')
        query = """
            CREATE OR REPLACE view product_move_record3 as(
            SELECT
                row_number() OVER (ORDER BY 1) as id,
                start_date as start_date,
                pm_out.product as product,
                pm_out.quantity as start_quantity,
                x_studio_doc_trans_code as trans_code,
                COALESCE(
                (
            SELECT 
                'Outgoing' AS io_code
            FROM 
                stock_move sm LEFT JOIN stock_picking sp on sm.picking_id = sp.id 
            WHERE 
                sm.product_id = pm_out.product AND
                sm.state in ('done') AND
                sm.location_id = 8 AND
                to_char(sm.date, 'YYYY-MM') = to_char(pm_out.start_date, 'YYYY-MM') AND
                ((sp.x_studio_doc_trans_code = sp_out.x_studio_doc_trans_code) OR
                (sp.x_studio_doc_trans_code IS NULL AND sp_out.x_studio_doc_trans_code IS NULL))
            GROUP BY
                sm.product_id,  
                x_studio_doc_trans_code,
                to_char(sm.date, 'YYYY-MM')
            ), 'No Data') AS io_code,
                COALESCE(
                (
            SELECT 
                SUM(product_qty) * -1
            FROM 
                stock_move sm LEFT JOIN stock_picking sp on sm.picking_id = sp.id 
            WHERE 
                sm.product_id = pm_out.product AND
                sm.state in ('done') AND
                sm.location_id = 8 AND
                to_char(sm.date, 'YYYY-MM') = to_char(pm_out.start_date, 'YYYY-MM') AND
                ((sp.x_studio_doc_trans_code = sp_out.x_studio_doc_trans_code) OR
                (sp.x_studio_doc_trans_code IS NULL AND sp_out.x_studio_doc_trans_code IS NULL))
            GROUP BY
                sm.product_id,  
                x_studio_doc_trans_code,
                to_char(sm.date, 'YYYY-MM')
            ), 0) AS quantity
            FROM product_move_product_move pm_out, (SELECT DISTINCT x_studio_doc_trans_code FROM stock_picking) AS sp_out
            UNION
            SELECT
                row_number() OVER (ORDER BY 1) as id,
                start_date as start_date,
                pm_out.product as product,
                pm_out.quantity as start_quantity,
                x_studio_doc_trans_code as trans_code,
                COALESCE(
                (
            SELECT 
                'Ingoing' AS io_code
            FROM 
                stock_move sm LEFT JOIN stock_picking sp on sm.picking_id = sp.id 
            WHERE 
                sm.product_id = pm_out.product AND
                sm.state in ('done') AND
                sm.location_dest_id = 8 AND
                to_char(sm.date, 'YYYY-MM') = to_char(pm_out.start_date, 'YYYY-MM') AND
                ((sp.x_studio_doc_trans_code = sp_out.x_studio_doc_trans_code) OR
                (sp.x_studio_doc_trans_code IS NULL AND sp_out.x_studio_doc_trans_code IS NULL))
            GROUP BY
                sm.product_id,  
                x_studio_doc_trans_code,
                to_char(sm.date, 'YYYY-MM')
            ), 'No Data') AS io_code,
                COALESCE(
                (
            SELECT 
                SUM(product_qty)
            FROM 
                stock_move sm LEFT JOIN stock_picking sp on sm.picking_id = sp.id 
            WHERE 
                sm.product_id = pm_out.product AND
                sm.state in ('done') AND
                sm.location_dest_id = 8 AND
                to_char(sm.date, 'YYYY-MM') = to_char(pm_out.start_date, 'YYYY-MM') AND
                ((sp.x_studio_doc_trans_code = sp_out.x_studio_doc_trans_code) OR
                (sp.x_studio_doc_trans_code IS NULL AND sp_out.x_studio_doc_trans_code IS NULL))
            GROUP BY
                sm.product_id,  
                x_studio_doc_trans_code,
                to_char(sm.date, 'YYYY-MM')
            ), 0) AS quantity
            FROM product_move_product_move pm_out, (SELECT DISTINCT x_studio_doc_trans_code FROM stock_picking) AS sp_out
        )
        """ 
        self._cr.execute(query)
    

