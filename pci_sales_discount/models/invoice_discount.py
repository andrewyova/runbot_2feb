# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
  
# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Vendor Refund
}
MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')
  
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
      
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit
            for discount_product in line.discount_m2m:
                if discount_product.id:
                    price_unit = price_unit * (1 - (discount_product.percentage or 0.0) / 100.0)
                      
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, 
                                                          line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': self.id,
                    'name': tax['name'],
                    'tax_id': tax['id'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
                    'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
                }
  
                # If the taxes generate moves on the same financial account as the invoice line,
                # propagate the analytic account from the invoice line to the tax line.
                # This is necessary in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id
  
                key = tax['id']
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
        return tax_grouped
      
      
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
      
    discount_m2m = fields.Many2many('discount.discount',string="Discounts")
    qty_returned = fields.Float(string='Returned', copy=False, digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    is_free = fields.Boolean('Free product', default=False)
      
    @api.one
    @api.depends('price_unit', 'discount_m2m', 'invoice_line_tax_ids', 'quantity', 'qty_returned',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit
        for discount_product in self.discount_m2m:
            if discount_product.id:
                price = price * (1 - (discount_product.percentage or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, 
                                                          product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
      
    product_tags = fields.Many2one('product.tags', "Tags") # this field added for dynamic report in account.invoice.report
    price_subtotal = fields.Monetary(string='Amount',
        store=True, readonly=True, compute='_compute_price')
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit notes.")
      
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.env.cr.execute("select pb.id from (select product_tags_id from product_tags_product_template_rel where product_template_id="+ str(self.product_id.product_tmpl_id.id) +") as data join  product_tags pb on pb.id = data.product_tags_id and pb.type = 'brand';")
            res = self.env.cr.dictfetchall()
            print("hhhhhhhhhhhhhhhh",res)
            if res:
                self.product_tags = res[0]['id'] or False
        return super(AccountInvoiceLine, self)._onchange_product_id()