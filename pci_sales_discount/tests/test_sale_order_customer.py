# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.exceptions import UserError, AccessError
from openerp.addons.account.tests.account_test_classes import AccountingTestCase

# from test_sale_common import TestSale


class TestSaleOrderCustomer(AccountingTestCase):  
        
        
    def testAddCustomerDiscountCustomer(self):
#         print "===============================================Check Product Tag==============================================="
        # Create Product Tag
        tag = self.env['product.tags'].create({
                            'status': True,
                            'type': 'brand',
                            'name': 'Aqua',
                        })
        self.assertTrue(tag.id != None)

#         print "========================================Make Discount Customer for Customer===================================="
        discount_customer = self.env['discount.discount'].create({'name':'Drink Customer',
                                                         'status' : True,
                                                         'percentage': 10.00,
                                                         'tags': tag.id,
                                                         'account_id' : 9,
                                                         'type':'volume',
                                                         'sequence_discount': '3',
                                                         })
        self.assertTrue(discount_customer.id != None)
        
#         print "=======================================Make Product with tag =================================================="
        product_tmpl = self.env['product.template'].create({ 
                                                            'name' : 'WaterCool 600ml',
                                                            'type' : 'consu',
                                                            'invoice_policy' : 'order',                                                            
                                                            'list_price' : 10.00,
                                                            'standard_price' : 0.00,
                                                            'tags' : [(6, 0, [tag.id])],
                                                            })
        product_tag_create = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl.id)])
        self.assertTrue(product_tmpl.id != None)
        
        product_tmpl_1 = self.env['product.template'].create({ 
                                                            'name' : 'WaterCool 1L',
                                                            'type' : 'consu',
                                                            'invoice_policy' : 'order',                                                            
                                                            'list_price' : 20.00,
                                                            'standard_price' : 0.00,
                                                            'tags' : [(6, 0, [tag.id])],
                                                            })
        product_tag_create_2 = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_1.id)])
         
#         print "========================================add Discount Customer to Customer======================================"
        customer_add_discount = self.env['res.partner'].create({'name':'Customer_test01',
                                                     'customer' : True,
                                                     'discount_customer' : [(6,0,[discount_customer.id])],
                                                     'property_account_receivable_id' : 9,
                                                     'property_account_payable_id' : 17,                                                     
                                                     })
        self.assertTrue(customer_add_discount.discount_customer != None)
#         print "============================Make Sale order based on discount Customer========================================="
        sale_order_discount = self.env['sale.order'].create({'partner_id':customer_add_discount.id,
                                                             'order_line':[(0, 0, {'name':product_tag_create.name ,
                                                                                   'product_id': product_tag_create.id,
                                                                                   'product_uom_qty': 2, 
                                                                                   'product_uom': 1, 
                                                                                   'price_unit': product_tag_create.list_price, 
                                                                                   'discount_m2m': [(6, 0, [discount_customer.id])]}),
                                                                            (0, 0, {'name':product_tag_create_2.name ,
                                                                                    'product_id': product_tag_create_2.id,
                                                                                    'product_uom_qty': 3, 
                                                                                    'product_uom': 1, 
                                                                                    'price_unit': product_tag_create_2.list_price, 
                                                                                    'discount_m2m': [(6, 0, [discount_customer.id])]})
                                                                           ],
                                                             })
        self.assertTrue(sale_order_discount.id != None)
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",sale_order_discount.amount_total
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",sale_order_discount.order_line

#         print "======================================Sale Order Confirm========================================================"
        
        sale_order_discount.action_confirm()
        self.assertTrue(sale_order_discount.state == 'sale')
        self.assertTrue(sale_order_discount.invoice_status == 'to invoice')
#         print "====================================check delivered order======================================================="
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",sale_order_discount.name
        stock_order_discount = self.env['stock.picking'].search([('origin','=',sale_order_discount.name)])
        
        stock_order_discount.force_assign()
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",stock_order_discount.pack_operation_product_ids
        for each in stock_order_discount.pack_operation_product_ids:
            print "------------------------------------------------------------ for",each.product_qty
            
        for each in stock_order_discount.pack_operation_product_ids:
            each.write({'qty_done': each.product_qty})
#         stock_order_discount.pack_operation_product_ids.write({'qty_done': stock_order_discount.pack_operation_product_ids.product_qty})
#         
        stock_order_discount.do_new_transfer()
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",stock_order_discount.state
        print "=============================================Create Invoice====================================================="
        sale_order_discount.action_invoice_create()
        invoice_order_discount = self.env['account.invoice'].search([('origin','=',sale_order_discount.name)])
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>.",invoice_order_discount.state
        invoice_order_discount.invoice_validate()
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>total invoice : ",invoice_order_discount.amount_total
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>has been validate.",invoice_order_discount.state
        self.assertTrue(sale_order_discount.amount_total == invoice_order_discount.amount_total,'ammount beda')
         

