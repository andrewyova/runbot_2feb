# -*- coding: utf-8 -*-
{
    "name": "PCI: Sales Discount",
    "version": "1.0",
    "author": "Port Cities",
    "website": "http://portcitiesindonesia.com",
    "category": "Generic Modules",
    "depends": ["sale","account_accountant","pci_product_tag"],
    "description": """
Add custom discount customer in SALE and invoice
""",
    "demo_xml":[],
    "data":[
        "security/ir.model.access.csv",
        "views/sales_discount_view.xml",
        "views/invoice_discount_view.xml",
    ],
    "active": False,
    "installable": True,
    "auto_install": False
}

