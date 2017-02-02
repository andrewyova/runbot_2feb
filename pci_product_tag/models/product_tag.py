# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError


class ProductTags(models.Model):
    _name = "product.tags"
    
    name = fields.Char('Name')
    status = fields.Boolean('Active')
    type = fields.Selection([('brand', 'Brand'),
                             ('general', 'General')], string = 'Type')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the tag must be unique !')
    ]
    
    
class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    tags = fields.Many2many('product.tags',string="Tags")
