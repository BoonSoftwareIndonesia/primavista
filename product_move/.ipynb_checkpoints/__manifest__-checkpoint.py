# -*- coding: utf-8 -*-
{
    'name': "product_move",

    'summary': """
        Test module for KPR Product Move""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': ['base','product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/calculate_onhold_view.xml',
        'views/views.xml',
        'views/product_move_view.xml',
        'views/product_move_record_view.xml',
        'views/product_move_record2_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
