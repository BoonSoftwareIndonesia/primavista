from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.http import request, Response

# set the x studio opt char value in stock move based on the value from PO and SO line
class StockRuleExt(models.Model):
    _inherit = 'stock.rule'

    # This sets the x_studio_opt_char_1 in stock move based on the x_studio_opt_char_1 value from the PO line
    # While creating stock.picking or stock.move, it impacts procurement/stock.rule 
    # So, you will have to add the values in stock.rule too
    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(StockRuleExt, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
        return res
    
    # This sets the x_studio_opt_char_1 in stock move based on the x_studio_line_no value from the SO line
    # While creating stock.picking or stock.move, it impacts procurement/stock.rule 
    # So, you will have to add the values in stock.rule too
    @api.model
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        group_id = False
        res = super(StockRuleExt, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        
        res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
        return res

class StockMoveExt(models.Model):
    _inherit = 'stock.move'
    x_studio_opt_char_1 = fields.Char('inwardLineOptChar1')

    
    
class StockReturnPickingExt(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    # We need to override create_returns() function from the stock.rule model instead of using automated actions 
    # to call the api_return_po() and api_return_so() functions to prevent multiple API logs from being sent 
    # to the WMS when there is a partial case
    def create_returns(self):
        
        # Call the super() method
        # The create_returns() function will call the _create_returns() function which will create a new stock picking 
        # (PO return receipt) for the returned products.
        # create_returns() will return res_id, which is obtained from the value of new_picking.id 
        # that is returned from calling _create_returns()
        new_picking = super(StockReturnPickingExt, self).create_returns()
        
        # Get the newly created return’s stock picking by searching through the stock.picking model
        curr_picking = request.env['stock.picking'].search([('id','=',int(new_picking['res_id']))])
                    
        if "IN" in curr_picking['origin']:
            # If the origin of the stock picking contains “IN” (such as WH/IN/0001) then it is a PO return
            self.env['stock.picking'].api_return_po(curr_picking)
        else:
            # If the origin of the stock picking contains “OUT” (such as WH/OUT/0001) then it is a SO return
            self.env['stock.picking'].api_return_so(curr_picking)
            
        return new_picking
    
    
    @api.model
    def _create_returns(self):
        # Override the _create_returns() function  to set the value of x_wms_rec_no and x_studio_doc_trans_code 
        # of the newly created return’s stock picking, stock moves, and stock move lines with the values 
        # from the origin stock picking.
        
        # Call the super() method. This will create a new stock picking for the PO return 
        # and return new_picking.id and picking_type_id
        new_picking, pick_type_id = super(StockReturnPickingExt, self)._create_returns()
        
        # Search for the newly created return’s stock picking
        curr_pick = request.env['stock.picking'].search([('id', '=', int(new_picking))], limit=1)
    
        trans_code = ""
        
        # Get the stock picking’s origin/source.
        in_num = curr_pick.origin
        # The origin will always start with “Return of ” (example: Return of WH/IN/0001)
        # so we need to slice the string to only get the origin of the stock picking (example: WH/IN/0001).
        in_num = in_num[10:]
        
        # Determine the trans code of the stock picking and store it into a variable called “trans_code”
        if "IN" in in_num:
            # If the origin contains the word “IN”, then the trans code of the stock picking is POR (PO Return) 
            # as it is a PO return
            trans_code = "POR"
        else:
            # If the origin contains the word “OUT”, then the trans code of the stock picking is GRN (Goods Received Note) 
            # as it is a SO return
            trans_code = "GRN"
        
        # Search for the origin stock picking which is the source/origin of the return’s stock picking
        source = request.env['stock.picking'].search([('name', '=', in_num)], limit=1)
        
        # Initialize a variable to store the x_wms_rec_no value of the current stock picking 
        wms_no = 0
        
        # Loop through the “source” variable. We need to loop because the search result returns a result set and not one record
        for pick in source:
            # Assign the origin’s x_wms_rec_no to the “wms_no” variable
            wms_no = pick.x_wms_rec_no

        # Set the value of x_wms_rec_no and x_studio_doc_trans_code for the return's stock picking
        curr_pick.write({'x_wms_rec_no': wms_no, 'x_studio_doc_trans_code':trans_code})
        # Set the value of x_wms_rec_no and x_studio_doc_trans_code for the return's stock moves
        curr_pick.move_lines.write({'x_wms_rec_no': wms_no})
        # Set the value of x_wms_rec_no and x_studio_doc_trans_code for the return's stock move lines
        curr_pick.move_lines.move_line_ids.write({'x_wms_rec_no': wms_no})
        
        return new_picking, pick_type_id
    