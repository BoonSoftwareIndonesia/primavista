# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api

class ProductMove(models.Model):
    _name = 'product_move.record4'
    _description = 'Record Report4'
    _auto = False

    id = fields.Integer(string="Id",readonly=True)
    product = fields.Many2one('product.product', string="Product",readonly=True)
    start_date = fields.Datetime(string="Start Date",readonly=True)
    start_quantity = fields.Float(string="Start Quantity",readonly=True)
    start_value = fields.Float(string="Start Value",readonly=True)
    PODR_In = fields.Float(string="In PODR",readonly=True)
    PODR_Out = fields.Float(string="Out PODR",readonly=True)
    GR_In = fields.Float(string="In GR",readonly=True)
    GR_Out = fields.Float(string="Out GR",readonly=True)
    undefined_In = fields.Float(string="In ",readonly=True)
    undefined_Out = fields.Float(string="Out ",readonly=True)
    CP_In = fields.Float(string="In CP",readonly=True)
    CP_Out = fields.Float(string="Out CP",readonly=True)
    OR_In = fields.Float(string="In OR",readonly=True)
    OR_Out = fields.Float(string="Out OR",readonly=True)
    GRN_In = fields.Float(string="In GRN",readonly=True)
    GRN_Out = fields.Float(string="Out GRN",readonly=True)
    POR_In = fields.Float(string="In POR",readonly=True)
    POR_Out = fields.Float(string="Out POR",readonly=True)
    GRA_In = fields.Float(string="In GRA",readonly=True)
    GRA_Out = fields.Float(string="Out GRA",readonly=True)
    total_in = fields.Float(string="Total IN",readonly=True)
    total_out = fields.Float(string="Total OUT",readonly=True)
    quantity_movement = fields.Float(string="Quantity Movement",readonly=True)
    final_quantity = fields.Float(string="Final Quantity",readonly=True)
    final_value = fields.Float(string="Final Value",readonly=True)
    value_in = fields.Float(string="Total Value IN",readonly=True)
    value_out = fields.Float(string="Total Value OUT",readonly=True)
    value_total = fields.Float(string="Total Value",readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'product_move_record4')
        query = """
            CREATE OR REPLACE view product_move_record4 as(
            select 
                row_number() OVER (ORDER BY 1) as id,
                pml.product as product, 
                pm.start_date as start_date, 
                pm.quantity as start_quantity, 
                pm.value as start_value,
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'PODR') as "PODR_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'PODR') as "PODR_Out",
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'GR') as "GR_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'GR') as "GR_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = '') as "undefined_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = '') as "undefined_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'CP') as "CP_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'CP') as "CP_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'OR') as "OR_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'OR') as "OR_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'GRN') as "GRN_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'GRN') as "GRN_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'POR') as "POR_In", 
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'POR') as "POR_Out", 
                sum(pml.quantity) filter (where pml.io_code ='IN' and pml.trans_code = 'GRA') as "GRA_In",
                sum(pml.quantity) filter (where pml.io_code ='OUT' and pml.trans_code = 'GRA') as "GRA_Out",
                sum(pml.quantity) filter (where pml.io_code='IN') as "total_in",
                sum(pml.quantity) filter (where pml.io_code='OUT') as "total_out",
                sum(pml.quantity) filter (where pml.io_code='IN') - sum(pml.quantity) filter (where pml.io_code='OUT') AS "quantity_movement",
                pm.quantity + (sum(pml.quantity) filter (where pml.io_code='IN') - sum(pml.quantity) filter (where pml.io_code='OUT')) AS "final_quantity",
                sum(pml.value) filter (where pml.io_code='IN') AS "value_in",
                sum(pml.value) filter (where pml.io_code='OUT') AS "value_out",
                sum(pml.value) filter (where pml.io_code='IN') + sum(pml.value) filter (where pml.io_code='OUT') AS "value_total",
                pm.value + (sum(pml.value) filter (where pml.io_code='IN') + sum(pml.value) filter (where pml.io_code='OUT')) AS "final_value"
            from product_move_line pml join product_move_product_move pm on pm.id = pml.pm
            group by pml.product, pm.start_date, start_quantity, pm.value
            order by pml.product, pm.start_date
        )
        """ 
        self._cr.execute(query)
    
