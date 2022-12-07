# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.record2'
    _description = 'Record2 Report'
    _auto = False

    id = fields.Integer(string="id",readonly=True)
    start_date = fields.Datetime(string="Start Date",readonly=True)
    ingoing = fields.Float(string="Ingoing",readonly=True)
    outgoing = fields.Float(string="Outgoing",readonly=True)
    product = fields.Many2one('product.product', string="Product",readonly=True)
    quantity_movement = fields.Float(string="Qty Movement",readonly=True)
    start_quantity = fields.Float(string="Start Qty",readonly=True)
    # quantity = fields.Float(string="Quantity")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'product_move_record2')
        query = """
            CREATE OR REPLACE view product_move_record2 as(
            select 
                row_number() OVER (ORDER BY 1) as id,
                pm.start_date as start_date,
                pm.product as product,
                pm.quantity AS start_quantity,
                (CASE WHEN it.total IS NULL THEN 0 ELSE it.total END) AS ingoing,
                (CASE WHEN ot.total IS NULL THEN 0 ELSE ot.total END) AS outgoing,
                (
                    CASE 
                        WHEN (it.total IS NULL AND ot.total IS NULL) THEN 0
                        WHEN ot.total IS NULL THEN it.total
                        WHEN it.total IS NULL THEN ot.total
                        ELSE it.total + ot.total
                    END
                ) AS quantity_movement
            from 
                product_move_product_move pm LEFT JOIN (
            select 
                pm.id,
                SUM(product_qty) * -1 AS Total
            from 
                product_move_product_move pm LEFT JOIN stock_move sm ON pm.product = sm.product_id
            where 
                state in ('done') AND
                location_id = 8 AND
                sm.date > pm.start_date AND
                EXTRACT(MONTH FROM sm.date) = (EXTRACT(MONTH FROM pm.start_date) + 1) AND
                EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
            group by pm.id, start_date, product_id, pm.quantity
            ) AS ot ON pm.id = ot.id LEFT JOIN (
            select 
                pm.id,
                SUM(product_qty) AS Total
            from 
                product_move_product_move pm JOIN stock_move sm ON pm.product = sm.product_id
            where 
                state in ('done') AND
                location_dest_id = 8 AND
                sm.date > pm.start_date AND
                EXTRACT(MONTH FROM sm.date) = (EXTRACT(MONTH FROM pm.start_date) + 1) AND
                EXTRACT(YEAR FROM sm.date) = EXTRACT(YEAR FROM pm.start_date)
            group by pm.id, start_date, product_id, pm.quantity
            ) AS it ON pm.id = it.id
        )""" 
        self._cr.execute(query)
    

