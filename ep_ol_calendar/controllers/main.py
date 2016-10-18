import simplejson
import urllib
import openerp
from openerp import http
from openerp.http import request
import openerp.addons.web.controllers.main as webmain
from openerp.addons.web.http import SessionExpiredException
from werkzeug.exceptions import BadRequest
import werkzeug.utils
import requests

url_return=''
resource_id='https://outlook.office365.com/'
api_endpoint='https://outlook.office365.com/api/v1.0'

class outlook_auth(http.Controller):

    @http.route('/ep_ol_calendar/sync',type='json',auth='user')
    def sync_data(self, arch, fields, model, **kw):        
        users_obj=request.registry['res.users']
        is_rtoken=users_obj.is_rtoken_active(request.cr,request.uid,kw['local_context']['uid'])
        if not is_rtoken:
            return {
                    'status':'need_rtoken',
                    'url':'https://login.microsoftonline.com/common/oauth2/authorize?client_id=&redirect_uri=http://test.net/ep_ol_calendar/authorize&response_type=code'
                    }
        if is_rtoken:
            return {
                    'status':'rtoken_present',
                    'url':'https://login.microsoftonline.com/common/oauth2/authorize?client_id=redirect_uri=http://test.net/ep_ol_calendar/authorize&response_type=code'
                    }

        return True
    
    @http.route('/ep_ol_calendar/authorize', type='http', auth="none")
    def authorize(self, **kw):
        redirect_uri = 'http://test.net/ep_ol_calendar/authorize'
#         registry = openerp.modules.registry.RegistryManager.get('test')
        registry=request.registry
        cr=request.cr
        uid=request.session.uid
        context=request.context
        print "\nCurrent User %s \n" %uid
        rtoken=registry.get('res.users').is_rtoken_active(cr,uid,uid)
        print "DB refresh token %s" %rtoken
        access_token_json=False
        
        if not rtoken:
            refresh_token_dict=registry.get('outlook.service').send_request(cr,uid,kw.get('code'),redirect_uri)
            refresh_token=refresh_token_dict.get('refresh_token')
            rtoken=refresh_token.encode('utf-8','ignore')
            access_token=registry.get('outlook.service').get_access_token_from_refresh_token(cr,uid,rtoken,resource_id)
            access_token_json=access_token.json()
            registry.get('outlook.service').set_all_tokens(cr,uid,access_token_json,context)
        else:
            try:
                access_token=registry.get('outlook.service').get_access_token_from_refresh_token(cr,uid,rtoken,resource_id)
            except:
                print "Could not process request"

            if access_token.status_code != 200:
                print "Refresh token may have expired",rtoken
            else:
                access_token_json=access_token.json()
                registry.get('outlook.service').set_access_token(cr,uid,access_token_json,context)
        
        if access_token_json:
            token=access_token_json['access_token']
            a={
                  "Subject": "Created through API",
                  "Body": {
                    "ContentType": "HTML",
                    "Content": "I think it will meet our requirements!"
                  },
                  "Start": "2016-02-02T18:00:00-08:00",
                  "StartTimeZone": "Pacific Standard Time",
                  "End": "2016-02-02T19:00:00-08:00",
                  "EndTimeZone": "Pacific Standard Time",
#                   "Attendees": [
#                     {
#                       "EmailAddress": {
#                         "Address": "shawn@test.com",
#                         "Name": "Shawn 123"
#                       },
#                       "Type": "Required"
#                     }
#                   ]
                }
            calendar=registry.get('outlook.service').get_events(cr,uid,api_endpoint,token,'startdatetime=2016-02-01T20:00:00.000Z&enddatetime=2016-02-29T20:00:00.000Z')
             
#             calendar=registry.get('outlook.service').get_events(cr,uid,api_endpoint,token,str(a))
            print "Calendar \n %s" %calendar
        else:
            print "Access token missing"
        
        return werkzeug.utils.redirect(url_return)