#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo Manifest file
#    @author Shawn Varghese
##############################################################################

{
    'name': 'Fetch Incoming Mails- Odoo',
    'version': '1.0',
    'description':'Module to fetch Incoming Mails and reassign attachments',
    'author': 'Shawn',
    'depends': ['mail'],
    'data': [
             'security/ir.model.access.csv',
             'inmail.xml',
             'inmail_data.xml'
             ],
    'demo':[],
    'installable':True,
    'auto_install': False,
}
