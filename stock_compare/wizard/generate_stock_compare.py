from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil import rrule
from datetime import datetime
from dateutil.relativedelta import relativedelta

class CalculateOnholdWizard(models.TransientModel):
    _name = 'stock_compare.generate_stock_compare.wizard'
    _description = 'Generate Stock Compare Report'

    def generate_stock_compare(self):
        self.env['stock_compare.wms_stock'].search([]).unlink()
        self.env['stock_compare.wms_stock_line'].search([]).unlink()
        self._calculate_wms_stock()
        self._calculate_odoo_stock()
        # self.test()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
        
    def _calculate_wms_stock(self):
        # WMS Stock Lines
        wms_stock_lines = self.env['stock_compare.wms_stock_line'].search([])

        for line in wms_stock_lines:
            stock_quants = False
            
            # Get the id from location name
            loc_id = self.env['stock.location'].search([('complete_name','=',line.location)]).id
            
            # Find the stock quant based on loc_id or loc_id + lot_id
            if line.lot_id == "NULL":
                stock_quants = self.env['stock.quant'].search_read([('product_id','=',line.product),('location_id','=',loc_id)])
            else:
                stock_quants = self.env['stock.quant'].search_read([('product_id','=',line.product),('location_id','=',loc_id),('lot_id','=', line.lot_id)])

            new_odoo_quantity = 0
            new_diff_quantity = line.wms_quantity
            
            # If stock_quants are available, sum the available_quantity in Odoo
            if stock_quants is not False:
                for s in stock_quants:
                    new_odoo_quantity += s['available_quantity']
                # Calculate the difference by using the formula wms_quantity - odoo_quantity
                new_diff_quantity = line.wms_quantity - new_odoo_quantity
                
            line.write({
                'odoo_quantity': new_odoo_quantity,
                'diff_quantity': new_diff_quantity
            })
    
    def test(self):
        test = self.env['stock.quant'].search_read([('product_id','=',207)])
        raise UserError(str(test))
        
    def _calculate_odoo_stock(self):
        # raise UserError("hey")
        # Odoo Stock Lines
        odoo_products = self.env['product.product'].search([])
        curr_wms_stock_id = self.env['stock_compare.wms_stock'].search([]).id

        for product in odoo_products:
            # stock_quants_dict = {}

            lot_done = -1
            loc_done = -1

            curr_sum = 0
            curr_lot = -1
            curr_loc = -1

            stock_quants = self.env['stock.quant'].search([('product_id','=',product.id)],order="location_id desc,lot_id desc")

#             for idx,stock_quant in enumerate(stock_quants):
                
#                 new_lot_id = stock_quant.lot_id
#                 if new_lot_id is False:
#                     new_lot_id = -2

#                 # Check if stock_quant is from different lot or wh
#                 if (new_lot_id != curr_lot) or (stock_quant.location_id != curr_loc):
#                     # Check to create new stock line or not using prev stock quant
#                     if (curr_lot != lot_done) and (curr_loc != loc_done):
#                         self._create_odoo_stock_line(product, curr_wms_stock_id, stock_quants[idx-1], curr_sum)

#                     # Check new stock_quant exists in wms stock line or not
#                     self._check_existing_wms_stock_line(lot_done, loc_done, product, stock_quant)

#                     # Reset
#                     curr_lot = new_lot_id
#                     curr_loc = stock_quant.location_id
#                     curr_sum = 0

#                 # If stock line already in wms stock line
#                 if (new_lot_id == lot_done) and (stock_quant.location_id == loc_done):
#                     continue

#                 #Odoo Only Stock Line
#                 curr_sum += stock_quant.available_quantity
                
#                 # create for last stock quant
#                 if idx+1 == len(stock_quants):
#                     self._create_odoo_stock_line(product, curr_wms_stock_id, stock_quants[idx], curr_sum)
                    
        return

        
    def _check_existing_wms_stock_line(self, lot_done, loc_done, product, stock_quant):
        # new_lot_id = stock_quant[0].lot_id.id
        # if new_lot_id is False:
        #     new_lot_id = -2
            
        # existing_wms_stock_line = self.env['stock_compare.wms_stock_line'].search([('product_id','=',product.id), ('location','=',stock_quant[0].location_id.id),('lot_id','=',new_lot_id)])
        
        new_lot_id = stock_quant[0].lot_id.id
        new_lot_name = ""
        
        if new_lot_id is not False:
            new_lot_name = stock_quant[0].lot_id.name
        else:
            new_lot_name = "NULL"
            new_lot_id = -2
        
        existing_wms_stock_line = self.env['stock_compare.wms_stock_line'].search([('product_id','=',product.id), ('warehouse','=',stock_quant[0].location_id.warehouse_id.name),('lot_name','=',new_lot_name)])
            
        if existing_wms_stock_line is not False:
            # If exist in WMS stock line
            lot_done = new_lot_id
            loc_done = stock_quant[0].location_id.id

        return

    def _calculate_stock_quant_dict(self, stock_quants_dict, stock_quant, curr_loc, curr_lot):
        if curr_loc not in stock_quants_dict:
            stock_quants_dict[curr_loc] = {}

        if curr_lot not in stock_quants_dict[curr_loc]:
            stock_quants_dict[curr_loc][curr_lot] = stock_quant.available_quantity

        # If curr_loc and curr_lot already in the dict
        stock_quants_dict[curr_loc][curr_lot] += stock_quant.available_quantity

        return 

    def _create_odoo_stock_line(self, product, curr_wms_stock_id, stock_quant, curr_sum):
        stock_line_model = self.env['stock_compare.wms_stock_line']
        
        location = self.env['stock.location'].search([('id','=',stock_quant[0].location_id.id)]).complete_name

        create_params = {
            "wms_stock_id" : curr_wms_stock_id,
            "product" : product.default_code,
            "product_id" : product.id,
            "odoo_quantity" : curr_sum,
            "wms_quantity" : 0,
            "lot_id" : stock_quant[0].lot_id.id,
            "location" : location,
            "warehouse" : stock_quant[0].location_id.warehouse_id.name,
            "remarks" : "NA",
            "diff_quantity" : curr_sum * -1
        }
        stock_line_model.create(create_params)
        return