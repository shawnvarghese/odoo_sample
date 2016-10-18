from  openerp.osv import fields,osv
from openerp import models
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import email_re, email_split
from openerp.tools import html2plaintext

class incoming_mail_ep(osv.osv):
    _name="incoming.mail.ep"
    _description = "Incoming E-mail Process"
    _inherit = ['mail.thread']
    
    _columns={
          'name': fields.char('Subject', required=True),
          'email_from': fields.char('Email', required=True),
          'email_cc': fields.text('Global CC'),
          'user_id': fields.many2one('res.users', 'Salesperson'),
          'partner_id': fields.many2one('res.partner', 'Partner'),
          'description': fields.text('Description'),
          'model': fields.char('Model'),
          'doc_number': fields.char('Document Number'),
          'doc_msg': fields.char('Document Message')
           }
    
    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        if custom_values is None:
            custom_values = {}
        subject = msg.get('subject')
        if not subject:
            return super(incoming_mail_ep, self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        doc_msg = ''
        doc_number = ''
        model = ''
        subject_array = subject.split(' ')
        
        '''
        Here we convert the split the subject line into a list separated by space.
        The first index will contain the document type(invoice, so, po etc.)
        The second index will contain the number of the document
        The third index onwards will contain any remaining text in the subject.
        Therefore, a subject line like:
        'Invoice INV/16/1288 payment received'
        will be converted to
        ['Invoice', 'INV/16/1288', 'payment', 'received']
        '''
        if not (subject_array and len(subject_array) > 1):
            return super(incoming_mail_ep, self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        
        doc_type = str(subject_array[0])
        doc_number = str(subject_array[1])
        if len(subject_array) > 2:
            doc_msg = ' '.join(subject_array[2:])
                
        if doc_type.lower() == 'invoice':
            model = 'account.invoice'
        elif doc_type.lower() == 'so':
            model = 'sale.order'
        elif doc_type.lower() == 'po':
            model = 'purchase.order'
        elif doc_type.lower() == 'do':
            model = 'stock.picking'
                 
        defaults = {
            'name':  subject,
            'email_from': msg.get('from'),
            'description': html2plaintext(msg.get('body')),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
            'model': model,
            'doc_number':doc_number,
            'doc_msg': doc_msg
        }

        return super(incoming_mail_ep, self).message_new(cr, uid, msg, custom_values=defaults, context=context)
    
    '''
    This function can be called by the button or the server action, as configured in the
    incoming e-mail server
    '''
    def map_message(self,cr,uid,ids,context=None):
        attachment_obj = self.pool.get('ir.attachment')
        for record in self.browse(cr,uid,ids,context=context):
            attachment_ids = attachment_obj.search(cr,uid, [('res_id','=',record.id),
                                                           ('res_model','=','incoming.mail.ep')],
                                                  context=context)

            if not attachment_ids:
                return False
            if not (record.model and record.doc_number and self.pool.get(record.model)):
                return False
            
#             Invoice is a special case where the number is the identifying factor, not the name
            doc_id = False
            if record.model == 'account.invoice':
                doc_id =  self.pool.get(record.model).search(cr,uid, [('number','=',record.doc_number)], context=context)
            else:
                doc_id = self.pool.get(record.model).search(cr,uid, [('name','=',record.doc_number)], context=context)
                
            if not doc_id:
                return False
            
            vals = {
                    'res_model':record.model,
                    'res_id':doc_id[0]
                    }
            
            for rec in attachment_ids:
                attachment_obj.write(cr, uid,rec, vals, context=context)
            
#             Post a message in the record chatter
            msg_body = 'New Attachment received \n%s' % (record.doc_msg)
            self.pool.get(record.model).message_post(cr,uid,doc_id,body=msg_body,context=context)
            
            return True
