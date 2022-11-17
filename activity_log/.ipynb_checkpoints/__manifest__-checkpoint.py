# -*- coding: utf-8 -*-
{
    'name': "activity_log",

    'summary': """
        Logging user activity of creating, editing, or deleting records""",

    'description': """
        Creating rules to specify actions (create, edit, or delete) and models are logged. The logged information contains time, user that did the activity, and the modification details.
    """,

    'author': "BoonSoftware Jakarta",
    'website': "https://www.boonsoftware.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/activity_log_view.xml',
        'views/rule_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
