from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta

class CalculateOnholdWizard(models.TransientModel):
    _name = 'stock_compare.generate_stock_compare.wizard'
    _description = 'Generate Stock Compare Report'

    def generate_stock_compare(self):
        # self.env['stock_compare.wms_stock'].search([]).unlink()
        # self.env['stock_compare.wms_stock_line'].search([]).unlink()
        self._calculate_wms_stock()
        self._calculate_odoo_stock()
        
    def _calculate_wms_stock(self):
        # WMS Stock Lines
        wms_stock_lines = self.env['stock_compare.wms_stock_line'].search([])

        for line in wms_stock_lines:
            
            wh_id = self.env['stock.location'].search([('complete_name','=',line.warehouse)]).id
            # raise UserError(str(wh_id))
            
            if line.lot_id == "NULL":
                stock_quants = self.env['stock.quant'].search_read([('product_id','=',line.product),('location_id','=',wh_id)])
            else:
                stock_quants = self.env['stock.quant'].search_read([('product_id','=',line.product),('location_id','=',wh_id),('lot_id','=', line.lot_id)])

            new_odoo_quantity = 0
            new_diff_quantity = line.wms_quantity

            if stock_quants is not False:
                for s in stock_quants:
                    new_odoo_quantity += s['available_quantity']
                    new_diff_quantity = line.wms_quantity - new_odoo_quantity
                
            line.write({
                'odoo_quantity': new_odoo_quantity,
                'diff_quantity': new_diff_quantity
            })
        
    def _calculate_odoo_stock(self):
        # raise UserError("hey")
        # Odoo Stock Lines
        odoo_products = self.env['product.product'].search([])
        curr_wms_stock_id = self.env['stock_compare.wms_stock'].search([]).id

        for product in odoo_products:
            # stock_quants_dict = {}

            lot_done = -1
            wh_done = -1

            curr_sum = 0
            curr_lot = -1
            curr_wh = -1

            stock_quants = self.env['stock.quant'].search([('product_id','=',product.id)],order="location_id desc,lot_id desc")
            # raise UserError(str(stock_quants))

            for idx,stock_quant in enumerate(stock_quants):
                # raise UserError("hey")
                new_lot_id = stock_quant.lot_id
                if new_lot_id is False:
                    new_lot_id = -2

                # Check if stock_quant is from different lot or wh
                if (new_lot_id != curr_lot) or (stock_quant.location_id != curr_wh):
                    # raise UserError("woi")
                    # Check to create new stock line or not using prev stock quant
                    if (curr_lot != lot_done) and (curr_wh != wh_done):
                        # raise UserError("cape")
                        self._create_odoo_stock_line(product, curr_wms_stock_id, stock_quants[idx-1], curr_sum)

                    # Check new stock_quant exists in wms stock line or not
                    self._check_existing_wms_stock_line(lot_done, wh_done, product, stock_quant)

                    # Reset
                    curr_lot = new_lot_id
                    curr_wh = stock_quant.location_id
                    curr_sum = 0

                # If stock line already in wms stock line
                if (new_lot_id == lot_done) and (stock_quant.location_id == wh_done):
                    continue

                #Odoo Only Stock Line
                curr_sum += stock_quant.available_quantity
        return

        
    def _check_existing_wms_stock_line(self, lot_done, wh_done, product, stock_quant):
        new_lot_id = stock_quant[0].lot_id.id
        if new_lot_id is False:
            new_lot_id = -2
            
        existing_wms_stock_line = self.env['stock_compare.wms_stock_line'].search([('product_id','=',product.id), ('warehouse','=',stock_quant[0].location_id.id),('lot_id','=',new_lot_id)])
        
        if existing_wms_stock_line is not False:
            # If exist in WMS stock line
            lot_done = new_lot_id
            wh_done = stock_quant[0].location_id.id

        return

    def _calculate_stock_quant_dict(self, stock_quants_dict, stock_quant, curr_wh, curr_lot):
        if curr_wh not in stock_quants_dict:
            stock_quants_dict[curr_wh] = {}

        if curr_lot not in stock_quants_dict[curr_wh]:
            stock_quants_dict[curr_wh][curr_lot] = stock_quant.available_quantity

        # If curr_wh and curr_lot already in the dict
        stock_quants_dict[curr_wh][curr_lot] += stock_quant.available_quantity

        return 

    def _create_odoo_stock_line(self, product, curr_wms_stock_id, stock_quant, curr_sum):
        stock_line_model = self.env['stock_compare.wms_stock_line']
        
        warehouse = self.env['stock.location'].search([('id','=',stock_quant[0].location_id.id)]).complete_name

        create_params = {
            "wms_stock_id" : curr_wms_stock_id,
            "product" : product.default_code,
            "product_id" : product.id,
            "odoo_quantity" : curr_sum,
            "wms_quantity" : 0,
            "lot_id" : stock_quant[0].lot_id.id,
            "warehouse" : warehouse,
            "remarks" : "NA",
            "diff_quantity" : curr_sum * -1
        }
        stock_line_model.create(create_params)
        return