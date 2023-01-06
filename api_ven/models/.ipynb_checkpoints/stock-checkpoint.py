from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.http import request, Response

# set the x studio opt char value in stock move based on the value from PO and SO line
class StockRuleExt(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(StockRuleExt, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['x_studio_opt_char_1'] = values.get('x_studio_opt_char_1', False)
        return res
    
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
    
    # this prevents multiple api logs from being sent to the wms when there is a partial case
    # and this triggers the api return po and so function that sends the original return receipt to wms
    def create_returns(self):
        
        new_picking = super(StockReturnPickingExt, self).create_returns()
        
        curr_picking = request.env['stock.picking'].search([('id','=',int(new_picking['res_id']))])
                    
        if "IN" in curr_picking['origin']:
            # po ret
            self.env['stock.picking'].api_return_po(curr_picking)
        else:
            self.env['stock.picking'].api_return_so(curr_picking)
            
        return new_picking
    
    # set the wms rec no and doc trans code value in stock picking when the return button is clicked in a DO or PO RCPT
    @api.model
    def _create_returns(self):
        new_picking, pick_type_id = super(StockReturnPickingExt, self)._create_returns()
        
        # Search for the new picking
        curr_pick = request.env['stock.picking'].search([('id', '=', int(new_picking))], limit=1)
    
        # Get the stock.picking source name
        trans_code = ""
        in_num = curr_pick.origin
        in_num = in_num[10:]
        if "IN" in in_num:
            trans_code = "POR"
        else:
            trans_code = "GRN"
        
        # Get the source stock.picking (origin)
        source = request.env['stock.picking'].search([('name', '=', in_num)], limit=1)
        
        # Set current stock.picking x_wms_rec_no to source stock.picking's 
        # (loop is mandatory as search returns ResultSet not one record)
        wms_no = 0
        
        for pick in source:
            wms_no = pick.x_wms_rec_no

        curr_pick.write({'x_wms_rec_no': wms_no, 'x_studio_doc_trans_code':trans_code})
        curr_pick.move_lines.write({'x_wms_rec_no': wms_no})
        curr_pick.move_lines.move_line_ids.write({'x_wms_rec_no': wms_no})
        return new_picking, pick_type_id
    