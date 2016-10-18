# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Shawn V.
##############################################################################

{
    'name': 'Calendar365',
    'version': '1.0',
    'category': 'General',
    'summary': 'Calendar365',
    'description': """ Calendar365 """,
    'author': 'Shawn',
    'depends': ['calendar','web_calendar'],
    'qweb': [ 
        "static/src/xml/ol_calendar_qweb.xml", 
    ],
    'data':['ol_calendar_data.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
