# -*- coding: utf-8 -*-
{
    'name': "BoonSoftware WMS and Odoo Module",

    'summary': """
        Boonsoftware Custom WMS,SAP, and Odoo Module""",

    'description': """
        This module is created by Boonsoftware for integration between WMS, SAP AVO, and Odoo
    """,

    'author': "BoonSoftware Jakarta",
    'website': "https://www.boonsoftware.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase', 'sale_management', 'stock', 'account', 'account_accountant'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/activity_log_view.xml',
#         'views/location.xml',
    ],
    
#     'assets': {
#         'web.assets_backend': [
#             'api_ven/static/src/js/checkin_button.js',
#         ],
#         'web.assets_qweb': [
#             'api_ven/static/src/xml/checkin_button_view.xml'
#         ]
#     },
    
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
