# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError
import datetime
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import logging
import string


class Discount(models.Model):
    _name = "discount.discount"
    
    name = fields.Char('Name', required=True)
    percentage = fields.Float('Percentage')
    expired_date = fields.Date(string='Expired Date')
    status = fields.Boolean('Status')
    type = fields.Selection([('volume', 'volume'), ('additional', 'additional'),
                             ('sale_order', 'sale_order'), ('extra', 'extra')],
                            string='Type', required=True, default='extra')
    tags = fields.Many2one('product.tags', 'Tags')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    sequence_discount = fields.Selection([('1', '1'), ('2', '2'),('3', '3'), ('4', '4'),('5', '5'), ('6', '6')],
                                         string='Sequence calculate discount', required=True, default='6',
                                         help='1 is higest level of discount')

        
class CustomerDiscountRes(models.Model):
    _inherit = "res.partner"
    
    discount_customer = fields.Many2many('discount.discount', 'discount_partner_rel',
                                        'partner_id', 'discount_id', string="Discount partner", copy=False, readonly=False)
    
class DiscountsSO(models.Model):
    _name = "sale.order.discounts"
    
    discount_id = fields.Many2one('discount.discount', 'Discount SO')
    order_id = fields.Many2one('sale.order', string='Order reference', required=True, ondelete='cascade', index=True, copy=False)

    @api.multi
    def unlink(self):
        for disc in self:
            order_id = disc.order_id.id
            discount_id = disc.discount_id.id
            self._cr.execute("select id from sale_order_line where order_id=%s" % order_id)
            line_ids = [x[0] for x in self._cr.fetchall()]
            query = "DELETE FROM discount_discount_sale_order_line_rel "\
                "where discount_discount_id=%s "\
                "and sale_order_line_id in %s"
            self._cr.execute(query, (discount_id,tuple(line_ids)))
            self.env['sale.order.line'].search([('id','in',line_ids)]).write({'date_change_disc': fields.datetime.now()})
            self.invalidate_cache()
            
        return super(DiscountsSO, self).unlink()
    
   
class CustomerOrder(models.Model):
    _inherit = "sale.order"
    
    discount_cust_order = fields.One2many('sale.order.discounts', 'order_id', string='Discount Sale Order')
    allow_finance = fields.Boolean('Can edit unit price', default=False)
    allow_sales = fields.Boolean('Can edit discount', default=True)
    
    @api.model
    def create(self, vals):
        if vals.get('client_order_ref'):
            temp_client_order_ref = vals['client_order_ref']
            vals['client_order_ref'] = temp_client_order_ref.upper()
        result = super(CustomerOrder, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        if vals.get('client_order_ref'):
            temp_client_order_ref = vals['client_order_ref']
            vals['client_order_ref'] = temp_client_order_ref.upper()
        res = super(CustomerOrder, self).write(vals)
        return res

    @api.multi
    def button_dummy(self):
        super(CustomerOrder, self).button_dummy()
        disc_cus = []
        dco_ids = []
        multitags_discounts = [] # 3 TYPE DISCOUNT (sale_order,volume,additional) with tags
        disc_tags = []
        global_discounts = []
        disc_tags_prods = []
        ''' GET ALL DISCOUNT GLOBAL (DISCOUNT TYPE : sale_order) '''
        for dco in self.discount_cust_order:
            dco_ids.append(dco.discount_id.id)
            multitags_discounts.append(dco.discount_id.id)
            if dco.discount_id.tags.id:
                disc_tags.append(dco.discount_id.tags.id)
            else:
                global_discounts.append(dco.discount_id.id)
        ''' GET ALL DISCOUNT CUSTOMER (DISCOUNT TYPE : volume and additional) '''
        disc_customers = self.partner_id.discount_customer
        for disc in disc_customers :
            disc_cus.append(disc.id)
            multitags_discounts.append(disc.id)
            if disc.tags.id:
                disc_tags.append(disc.tags.id)
            
        querygetprod = ""
        if len(disc_tags)==0:
            querygetprod = "select product_template_id from product_tags_product_template_rel "
        elif len(disc_tags)==1:
            querygetprod = "select product_template_id from product_tags_product_template_rel "\
                           "where product_tags_id = %s" % disc_tags[0]
        else:
            querygetprod = "select product_template_id from product_tags_product_template_rel "\
                           "where product_tags_id in %s" % str(tuple(disc_tags))

        if querygetprod!= "":
            self._cr.execute(querygetprod)
            prods = self._cr.fetchall()
            for prod in prods :
                disc_tags_prods.append(prod[0])

        for sol in self.order_line :
            querygettags = "select product_tags_id from product_tags_product_template_rel "\
                           "where product_template_id=%s limit 1" % sol.product_id.product_tmpl_id.id
            self._cr.execute(querygettags)
            sol_prod_tags = self._cr.fetchall()
            found_tags = False
            extra_disc_ids = []
            # keep extra discount
            for extra in sol.discount_m2m:
                if extra.type == 'extra':
                    extra_disc_ids.append(extra.id)

            if sol.product_id.product_tmpl_id.id in disc_tags_prods:
                found_tags = True
            if found_tags:
                disc_ids_temp = []
                # improve this get object in outside loop insert into array then loop manual without search again
                prod_tags_disc = self.env['discount.discount'].search([('tags','=',sol_prod_tags[0][0]), 
                                                                        ('id','in',multitags_discounts)])
                for pbd in prod_tags_disc:
                    disc_ids_temp.append(pbd.id)
                # discount global apply to all product
                for _global in global_discounts:
                    disc_ids_temp.append(_global)
                sol.update({"discount_m2m" : [(6, 0, disc_ids_temp + extra_disc_ids)] })
            else:
                disc_ids_temp = []
                for _global in global_discounts:
                    disc_ids_temp.append(_global)
                sol.update({"discount_m2m" : [(6, 0, disc_ids_temp + extra_disc_ids)] })
        return True


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
 
    editable_discount = fields.Boolean(compute='_change_view_sales', string='Can Edit Discount', default=False)
    editable_price = fields.Boolean(compute='_change_view_finance', string='Can Edit Unit Price', default=False)
    price_unit_hidden = fields.Float('Unit Price Hidden', digits=dp.get_precision('Product Price'), default=0.0)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Finish Goods'), required=True, default=1)
    qty_delivered = fields.Float(string='Delivered', copy=False, digits=dp.get_precision('Finish Goods'), default=0)
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty', string='To Invoice', store=True, readonly=True,
        digits=dp.get_precision('Finish Goods'), default=0)
    qty_invoiced = fields.Float(
        compute='_get_invoice_qty', string='Invoiced', store=True, readonly=True,
        digits=dp.get_precision('Finish Goods'), default=0)
 
    @api.depends('order_id.allow_sales')
    def _change_view_sales(self):
        for line in self:
            line.update({
                         'editable_discount' : line.order_id.allow_sales,
                         'price_unit' : line.price_unit_hidden if line.price_unit <= 0 else line.price_unit 
                         })
             
    @api.depends('order_id.allow_finance')
    def _change_view_finance(self):
        for line in self:
            line.update({
                         'editable_price' : line.order_id.allow_finance,
                         'price_unit' : line.price_unit_hidden if line.price_unit <= 0 else line.price_unit 
                         })
 
    @api.onchange('product_uom_qty')
    def _onchange_product_id_check_availability(self):
        return
     
    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if not float_is_zero(qty, precision_digits=precision):
                if line.qty_delivered - line.qty_returned > 0:
                    vals = line._prepare_invoice_line(qty=qty)
                    vals.update({'invoice_id': invoice_id, 'sale_line_ids': [(6, 0, [line.id])]})
                    self.env['account.invoice.line'].create(vals)
 
    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced', 'qty_returned')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs onyl in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        - returned: the quantity returned by customer
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            elif line.qty_invoiced>0 and line.qty_invoiced==(line.qty_delivered-line.qty_returned):
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and\
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'
                 
    @api.depends('product_uom_qty', 'discount_m2m', 'qty_returned', 'price_unit', 'tax_id','date_change_disc', 'qty_delivered')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit
            for discount_product in line.discount_m2m:
                if discount_product.id:
                    price = price * (1 - (discount_product.percentage or 0.0) / 100.0)
            delivered = line.qty_delivered if line.qty_delivered>0 else line.product_uom_qty
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, 
                                                delivered - line.qty_returned, 
                                                product=line.product_id, partner=line.order_id.partner_id)
            if line.is_free:
                line.update({
                    'price_tax': (taxes['total_included'] - taxes['total_excluded']) * -1,
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'] * -1.0,
                    'price_after_discounts' : price,
                })
            else:
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                    'price_after_discounts' : price,
                })
    @api.one
    def update_amount(self):
        price = self.price_unit
        for discount_product in self.discount_m2m:
            if discount_product.id:
                price = price * (1 - (discount_product.percentage or 0.0) / 100.0)
        delivered = self.qty_delivered if self.qty_delivered>0 else self.product_uom_qty
        taxes = self.tax_id.compute_all(price, self.order_id.currency_id, 
                                            delivered - self.qty_returned, 
                                            product=self.product_id, partner=self.order_id.partner_id)
        self.update({
            'price_tax': taxes['total_included'] - taxes['total_excluded'],
            'price_total': taxes['total_included'],
            'price_subtotal': taxes['total_excluded'],
            'price_after_discounts' : price,
        })
     
    @api.depends('product_id.invoice_policy', 'order_id.state')
    def _compute_qty_delivered_updateable(self):
        for line in self:
            line.qty_delivered_updateable = line.product_id.invoice_policy in ('order', 'delivery') and line.order_id.state == 'sale' and line.product_id.track_service == 'manual'
 
    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
 
    @api.depends('invoice_lines.invoice_id.state', 'invoice_lines.quantity')
    def _get_invoice_qty(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO.
        """
        for line in self:
            qty_invoiced = 0.0
            for invoice_line in line.invoice_lines:
                if invoice_line.invoice_id.state != 'cancel':
                    if invoice_line.invoice_id.type == 'out_invoice':
                        qty_invoiced += invoice_line.quantity
                    elif invoice_line.invoice_id.type == 'out_refund':
                        qty_invoiced -= invoice_line.quantity
            line.qty_invoiced = qty_invoiced
 
    @api.depends('price_subtotal', 'product_uom_qty')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0
         
    @api.model
    def addTaxToUnitPrice(self):
        acc_tax = self.env['account.tax']
        tax_id = acc_tax.search([('type_tax_use','=','sale')], limit=1)
        self.price_unit = self.price_unit + (self.price_unit * ((tax_id.amount or 0.0)/ 100.0))
 
    @api.multi
    def checkDiscountExist(self, sol_id, disc_id): 
        if not disc_id:
            return False
        self.env.cr.execute('''SELECT COUNT(*) 
                        FROM discount_discount_sale_order_line_rel 
                            WHERE sale_order_line_id=%s and discount_discount_id=%s''' ,(sol_id,disc_id))  
        res = self.env.cr.fetchone()
        if len(res)==0:
            return False
        else:
            return res[0]==1
     
     
    @api.multi
    def _action_procurement_create(self):
        """
        Create procurements based on quantity ordered. If the quantity is increased, new
        procurements are created. If the quantity is decreased, no automated action is taken.
         
        replace the old function to avoid calculation for free product
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        new_procs = self.env['procurement.order'] #Empty recordset
        for line in self:
            if line.state != 'sale' or line.is_free:
                continue
            qty = 0.0
            for proc in line.procurement_ids:
                qty += proc.product_qty
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                return False
            if not line.order_id.procurement_group_id:
                vals = line.order_id._prepare_procurement_group()
                line.order_id.procurement_group_id = self.env["procurement.group"].create(vals)
 
            vals = line._prepare_order_line_procurement(group_id=line.order_id.procurement_group_id.id)
            vals['product_qty'] = line.product_uom_qty - qty
            new_proc = self.env["procurement.order"].create(vals)
            new_procs += new_proc
        new_procs.run()
        return new_procs
                 
    @api.model
    def create(self, values):
        if values['product_uom_qty']<=0:
            # it mean can't create sale.order.line
            return self
        ir_model_data = self.env['ir.model.data']
        finance_id = ir_model_data.get_object_reference('account', 'group_account_user')[1]
        is_finance = False
        for group in self.env.user.groups_id:
            if group.id == finance_id:
                is_finance = True
                break
        if values.get('price_unit'):
            values['price_unit_hidden'] = values['price_unit']
        elif values.get('price_unit_hidden'):
            values['price_unit'] = values['price_unit_hidden']
        line = super(SaleOrderLine, self).create(values)
        return line
     
    @api.multi
    def write(self, values):
        ir_model_data = self.env['ir.model.data']
        finance_id = ir_model_data.get_object_reference('account', 'group_account_user')[1]
        is_finance = False
        for group in self.env.user.groups_id:
            if group.id == finance_id:
                is_finance = True
                break
 
        if values.get('price_unit'):
            values['price_unit_hidden'] = values['price_unit']
        elif values.get('price_unit_hidden'):
            values['price_unit'] = values['price_unit_hidden']
        line = super(SaleOrderLine, self).write(values)        
        return line
 
    @api.model
    def GetDiscountTags(self, partner_id, line):
        '''
        maybe can removed this method :: try to set discount use onchange_prodoct_id
        RESULT DISCOUNT IDS FROM CUSTOMER WHICH MATCH WITH PRODUCT TAGS
        @PARAM : line => SALE ORDER LINE OBJECT
        @PARAM : partner_id => GET FROM SALE ORDER
        '''
        result = []
        list_disc = partner_id.discount_customer
        product_template = line.product_id.product_tmpl_id.id
        product_template = self.env['product.template'].search([('id','=',product_template)])
        product_tags = product_template.tags
        for discount in list_disc:
            for tag in product_tags:
                # CHECK TAG DISCOUNT
                if tag.id == discount.tags.id and discount.status:
                    result.append(discount.id)
        return result
     
    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty=qty)
        res.pop("discount",None)
        if self.is_free:
            res.update({"price_unit" : (res['price_unit'] * -1)})
        disc_ids = []
        for d in self.discount_m2m:
            disc_ids.append(d.id)
        res.update({"product_tags" : self.product_tags.id,"quantity" : self.qty_delivered - self.qty_returned, 
                    "qty_returned" : self.qty_returned or 0.0, "discount_m2m" : [(6, 0, disc_ids)], 
                    "is_free" : self.is_free})
        return res
     
    @api.multi
    def _get_delivered_qty(self):
        self.ensure_one()
        return_qty = 0.0
        '''
        select sum(product_uom_qty),product_uom,location_id from stock_move where picking_id in (107044, 107043, 107042) and product_id = 3 group by location_id,product_uom;
        '''      
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "internal":
                return_qty += move.product_uom_qty
        self.qty_returned = return_qty
        return super(SaleOrderLine, self)._get_delivered_qty()
     
    product_tags = fields.Many2one('product.tags', "Tags")
    date_change_disc = fields.Datetime(string='Registration Date', default=lambda self: fields.datetime.now())
    discount_m2m = fields.Many2many('discount.discount',string="Discounts")
    qty_returned = fields.Float(string='Returned', copy=False,
                                 digits=dp.get_precision('Finish Goods'), default=0)
    price_after_discounts = fields.Float('Unit Price After Discount', default=0.0)
    is_free = fields.Boolean('Free product', default=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
     
    @api.multi
    @api.onchange('product_id','is_free')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}
 
        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not (self.product_uom and (self.product_id.uom_id.category_id.id == self.product_uom.category_id.id)):
            vals['product_uom'] = self.product_id.uom_id
        partner_id =self.order_id.partner_id.id
        if not partner_id:
            raise UserError(_("Please, fill customer first."))
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=partner_id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name
         
        self._compute_tax_id()
 
        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = vals['price_unit_hidden'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
         
        if not self.is_free:
            sql = " select discount_id as d,tags as b from  "\
                     " (select * from "\
                     "   (select discount_id from discount_partner_rel where partner_id = "+ str(partner_id) +") as disc_cust  "\
                     "   join discount_discount dd on dd.id = disc_cust.discount_id and dd.status = True) as tags_cust "\
                     "   join (select id from (select product_tags_id from product_tags_product_template_rel where product_template_id="+ str(self.product_id.product_tmpl_id.id) +") as data "\
                     "   join product_tags pb on pb.id = data.product_tags_id and pb.type = 'brand') as fixed_tags  "\
                     "   on fixed_tags.id=tags_cust.tags; "
            self.env.cr.execute(sql)
            res = self.env.cr.dictfetchall()
            if res:
                vals['discount_m2m'] = [d['d'] for d in res]
                vals['product_tags'] = res[0]['b']
            else:
                self.env.cr.execute("select pb.id from (select product_tags_id from product_tags_product_template_rel where product_template_id="+ str(self.product_id.product_tmpl_id.id) +") as data join  product_tags pb on pb.id = data.product_tags_id and pb.name ilike 'tags:%';")
                res = self.env.cr.dictfetchall()
                if res:
                    vals['product_tags'] = res[0]['id']
        self.update(vals)
        return {'domain': domain}


