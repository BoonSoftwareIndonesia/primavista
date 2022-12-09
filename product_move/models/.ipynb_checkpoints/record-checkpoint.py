# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.record'
    _description = 'Record Report'
    _auto = False

    id = fields.Integer(string="Id",readonly=True)
    start_date = fields.Datetime(string="Start Date",readonly=True)
    io_code = fields.Char(string="IO Code",readonly=True)
    product = fields.Many2one('product.product', string="Product",readonly=True)
    start_quantity = fields.Float(string="Start Quantity",readonly=True)
    quantity = fields.Float(string="Quantity",readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'product_move_record')
        query = """
            CREATE OR REPLACE view product_move_record as(
            SELECT
                row_number() OVER (ORDER BY 1) as id,
                pm_out.start_date as start_date,
                pm_out.quantity AS start_quantity,
                pm_out.product as product,	
                t1.IO_code as io_code,
                t1.total as quantity
            FROM
                product_move_product_move pm_out JOIN (	
            select
                pm.id,
                pm.start_date,
                pm.product,
                pm.quantity AS start_quantity,
                'Ingoing' AS IO_code,
                (
                    CASE WHEN EXISTS (
                            SELECT product_qty FROM stock_move sm WHERE
                            state in ('done') AND
                            location_dest_id = 8 AND
                            product_id = pm.product AND
                            EXTRACT(MONTH FROM sm.date) = EXTRACT(MONTH FROM pm.start_date) AND
                            EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
                    ) THEN (
                            SELECT SUM(product_qty) FROM stock_move sm WHERE
                            state in ('done') AND
                            location_dest_id = 8 AND
                            product_id = pm.product AND
                            EXTRACT(MONTH FROM sm.date) = EXTRACT(MONTH FROM pm.start_date) AND
                            EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
                    ) ELSE 0 END
                ) AS Total
            from 
                product_move_product_move pm
            UNION
            select
                pm.id, 
                pm.start_date,
                pm.product,
                pm.quantity AS start_quantity,
                'Outgoing' AS IO_code,
                (
                    CASE WHEN EXISTS (
                            SELECT product_qty FROM stock_move sm WHERE
                            state in ('done') AND
                            location_id = 8 AND
                            product_id = pm.product AND
                            EXTRACT(MONTH FROM sm.date) = EXTRACT(MONTH FROM pm.start_date) AND
                            EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
                    ) THEN ((
                            SELECT SUM(product_qty) FROM stock_move sm WHERE
                            state in ('done') AND
                            location_id = 8 AND
                            product_id = pm.product AND
                            EXTRACT(MONTH FROM sm.date) = EXTRACT(MONTH FROM pm.start_date) AND
                            EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
                    ) * -1) ELSE 0 END
                ) AS Total
            from 
                product_move_product_move pm
            ) as t1 ON pm_out.id = t1.id
            )
        """ 
        self._cr.execute(query)
    

