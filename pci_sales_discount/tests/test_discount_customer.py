# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase

class TestMessage(TransactionCase):
    # at_install = False
    # post_install = True

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')


    def setUp(self):
        ds = self.env['product.tags'].create({
                            'status': 1,
                            'type': 'Brand',
                            'name': 'Discount',
                        })
                # self.assertEqual(ds.status, 1)
        #
        # self.products = {
        #     'name': 'Lenovo',
        #     'product_id': 'product_product_1',
        #     'price_unit': 600,
        #     'tags':'Discount',
        # }
        # self.assertEqual(ds.name, self.products.tags)
        # self.assertEqual('foo'.upper(), 'FOO')
        #
        #


























    # def Tags(self):
    #     ds = self.env['product.tags'].create({
    #                 'status': 1,
    #                 'type': 'Brand',
    #                 'name': 'Discount',
    #             })
    #     self.assertEqual(ds.status, 1)

    # self.assertTrue(so.state == 'sent', 'Sale: state after sending is wrong')

# # Part of Odoo. See LICENSE file for full copyright and licensing details.
# from openerp.exceptions import UserError, AccessError
# from openerp.tests.common import TransactionCase
# from datetime import datetime
#
# class TestOnchangeProductId(TransactionCase):
#
#     def test_discount_customer(self):
#         ds = self.env['discount.discount'].create({
#             'status' : self.status,
#             'Tags' : self.tags,
#             'percentage' : self.percentage,
#             'account_id' : self.account_id,
#             'name' : self.name,
#             'expired_date' : datetime,
#             'type' : self.type,
#             'sequence_discount' : self.sequence_discount
#         })
#
