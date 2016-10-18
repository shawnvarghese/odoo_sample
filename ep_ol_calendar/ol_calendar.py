# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Shawn V.
#    OAUTH authentication based on @jasonjoh REST API conenctor sample 
##############################################################################

import openerp
from openerp.http import request
from openerp.osv import osv,fields
from openerp import SUPERUSER_ID,models,api
from openerp.tools.translate import _
from datetime import datetime,timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import requests
import werkzeug.urls
import urllib2
import simplejson
import base64
import json
import uuid

import logging
_logger = logging.getLogger(__name__)

verifySSL=True
access_token_url=''
client_id=''
client_secret=''
        
class res_users(osv.osv):
    _inherit="res.users"
    
    _columns={
              'ol_rtoken':fields.char('Refresh Token'),
              'ol_atoken':fields.char('Access Token'),
              'ol_rtoken_valid':fields.datetime('Token Validity'),
              'ol_last_sync_date':fields.datetime('Last Sync Date'),
              }

    def is_rtoken_active(self,cr,uid,user_id,context=None):
        self_browse_obj=self.browse(cr,uid,user_id)
        if self_browse_obj.ol_rtoken and self_browse_obj.ol_rtoken_valid > str(datetime.now()):
            return self_browse_obj.ol_rtoken
                
        return False
    
class outlook_service(osv.osv):
    _name="outlook.service"
    
    def set_access_token(self,cr,uid,access_token,context=None):
        access_token_val=access_token.get('access_token').encode('utf-8','ignore')
        vals={}
        vals['ol_atoken']=access_token_val
        self.pool.get('res.users').write(cr,SUPERUSER_ID,uid,vals,context=context)
        
        return True
    
    def set_all_tokens(self,cr,uid,access_token,context=None):
#         print "Refresh Token set",refresh_token
        refresh_token=access_token.get('refresh_token').encode('utf-8','ignore')
        refresh_token_validity=datetime.now() + timedelta(milliseconds=int(access_token.get('expires_on'))-60000)
        access_token_val=access_token.get('access_token').encode('utf-8','ignore')
         
        vals={}
        vals['ol_rtoken']=refresh_token
        vals['ol_rtoken_valid']=refresh_token_validity
        vals['ol_atoken']=access_token_val        
        
        print "vals",vals,"\nsuperid",SUPERUSER_ID,"\nuid",uid
        self.pool.get('res.users').write(cr,SUPERUSER_ID,uid,vals,context=context)

        return True
    
    def get_access_token_from_refresh_token(self,cr,uid,refresh_token, resource_id):
#         logger.debug('Entering get_access_token_from_refresh_token.')
#         logger.debug('  refresh_token: {0}'.format(refresh_token))
#         logger.debug('  resource_id: {0}'.format(resource_id))
        
        post_data = { 'grant_type' : 'refresh_token',
                      'client_id' : client_id,
                      'client_secret' : client_secret,
                      'refresh_token' : refresh_token,
                      'resource' : resource_id }
                      
        r = requests.post(access_token_url, data = post_data, verify = verifySSL)
        
#         logger.debug('Response: {0}'.format(r.json()))
        # Return the token as a JSON object
#         logger.debug('Leaving get_access_token_from_refresh_token.')
        return r
    
    
    def send_request(self,cr,uid,auth_code,redirect_uri,context=None):
#         logger.debug('Entering get_access_info_from_authcode.')
#         logger.debug('  auth_code: {0}'.format(auth_code))
#         logger.debug('  redirect_uri: {0}'.format(redirect_uri))
#         
#         logger.debug('Sending request to access token endpoint.')
        discovery_resource='https://api.office.com/discovery/'

        post_data = { 'grant_type' : 'authorization_code',
                      'code' : auth_code,
                      'redirect_uri' : redirect_uri,
                      'resource' : discovery_resource,
                      'client_id' : client_id,
                      'client_secret' : client_secret 
                    }
        r = requests.post(access_token_url, data = post_data, verify = verifySSL)
#         logger.debug('Received response from token endpoint.')
#         logger.debug(r.json())
        
        try:
            discovery_service_token = r.json()['access_token']
#             logger.debug('Extracted access token from response: {0}'.format(discovery_service_token))
        except:
#             logger.debug('Exception encountered, setting token to None.')
            discovery_service_token = None

        if (discovery_service_token):
            # Add the refresh token to the dictionary to be returned
            # so that the app can use it to request additional access tokens
            # for other resources without having to re-prompt the user.
            discovery_result = self.do_discovery(cr,uid,discovery_service_token)
#             logger.debug('Discovery completed.')
            discovery_result['refresh_token'] = r.json()['refresh_token']
            
            # Get the user's email from the access token and add to the
            # dictionary to be returned.
            json_token = self.parse_token(cr,uid,discovery_service_token)
#             logger.debug('Discovery token after parsing: {0}'.format(json_token))
            discovery_result['user_email'] = json_token['upn']
#             logger.debug('Extracted email from token: {0}'.format(json_token['upn']))
#             logger.debug('Leaving get_access_info_from_authcode.')
            return discovery_result
        else:
#             logger.debug('Leaving get_access_info_from_authcode.')
            return None
        
    def do_discovery(self,cr,uid,token):
#         logger.debug('Entering do_discovery.')
#         logger.debug('  token: {0}'.format(token))
        discovery_endpoint = 'https://api.office.com/discovery/v1.0/me/services'
        
        headers = { 'Authorization' : 'Bearer {0}'.format(token),
                    'Accept' : 'application/json' }
        r = requests.get(discovery_endpoint, headers = headers, verify = verifySSL)
        
        discovery_result = {}
        
        for entry in r.json()['value']:
            capability = entry['capability']
    #         logger.debug('Capability found: {0}'.format(capability))
            discovery_result['{0}_resource_id'.format(capability)] = entry['serviceResourceId']
            discovery_result['{0}_api_endpoint'.format(capability)] = entry['serviceEndpointUri']
    #         logger.debug('  Resource ID: {0}'.format(entry['serviceResourceId']))
    #         logger.debug('  API endpoint: {0}'.format(entry['serviceEndpointUri']))
            
#         logger.debug('Leaving do_discovery.')
        return discovery_result

    def parse_token(self,cr,uid,encoded_token):
#     logger.debug('Entering parse_token.')
#     logger.debug('  encoded_token: {0}'.format(encoded_token))
        try:
            # First split the token into header and payload
            token_parts = encoded_token.split('.')
            
            # Header is token_parts[0]
            # Payload is token_parts[1]
    #         logger.debug('Token part to decode: {0}'.format(token_parts[1]))
            
            decoded_token = self.decode_token_part(cr,uid,token_parts[1])
    #         logger.debug('Decoded token part: {0}'.format(decoded_token))
    #         logger.debug('Leaving parse_token.')
            return json.loads(decoded_token)
        except:
            return 'Invalid token value: {0}'.format(encoded_token)

    def decode_token_part(self,cr,uid,base64data):
#         logger.debug('Entering decode_token_part.')
#         logger.debug('  base64data: {0}'.format(base64data))
    
        # base64 strings should have a length divisible by 4
        # If this one doesn't, add the '=' padding to fix it
        leftovers = len(base64data) % 4
#         logger.debug('String length % 4 = {0}'.format(leftovers))
        if leftovers == 2:
            base64data += '=='
        elif leftovers == 3:
            base64data += '='
        
#         logger.debug('String with padding added: {0}'.format(base64data))
        decoded = base64.b64decode(base64data)
#         logger.debug('Decoded string: {0}'.format(decoded))
#         logger.debug('Leaving decode_token_part.')
#         print "decoded",decoded.decode('utf-8')
        return decoded.decode('utf-8')
    
    def make_api_call(self,cr,uid,method, url, token, payload = None):
        # Send these headers with all API calls
        headers = { 'User-Agent' : 'Odoo',
                    'Authorization' : 'Bearer {0}'.format(token),
                    'Accept' : 'application/json',
                    'Prefer': 'odata.track-changes' }
                    
        # Use these headers to instrument calls. Makes it easier
        # to correlate requests and responses in case of problems
        # and is a recommended best practice.
        request_id = str(uuid.uuid4())
        instrumentation = { 'client-request-id' : request_id,
                            'return-client-request-id' : 'true'
                            }
                             
        headers.update(instrumentation)
        print "Request URL",url
        response = None
#         url="https://outlook.office365.com/api/v1.0/me/calendarview?startdatetime=2015-05-24T20:00:00.000Z&enddatetime=2015-05-31T20:00:00.000Z"
        if (method.upper() == 'GET'):
#             logger.debug('{0}: Sending request id: {1}'.format(datetime.datetime.now(), request_id))
            response = requests.get(url, headers = headers, verify = verifySSL)
        elif (method.upper() == 'DELETE'):
#             logger.debug('{0}: Sending request id: {1}'.format(datetime.datetime.now(), request_id))
            response = requests.delete(url, headers = headers, verify = verifySSL)
        elif (method.upper() == 'PATCH'):
            headers.update({ 'Content-Type' : 'application/json' })
#             logger.debug('{0}: Sending request id: {1}'.format(datetime.datetime.now(), request_id))
            response = requests.patch(url, headers = headers, data = payload, verify = verifySSL)
        elif (method.upper() == 'POST'):
            headers.update({ 'Content-Type' : 'application/json' })
#             logger.debug('{0}: Sending request id: {1}'.format(datetime.datetime.now(), request_id))
            response = requests.post(url, headers = headers, data = payload, verify = verifySSL)
#     
# #         if (not response is None):
# #             logger.debug('{0}: Request id {1} completed. Server id: {2}, Status: {3}'.format(datetime.datetime.now(), 
# #                                                                                              request_id,
# #                                                                                              response.headers.get('request-id'),
# #                                                                                              response.status_code))
        return response
    
    def get_events(self,cr,uid,calendar_endpoint, token, parameters = None):
#         logger.debug('Entering get_events.')
#         logger.debug('  calendar_endpoint: {0}'.format(calendar_endpoint))
#         logger.debug('  token: {0}'.format(token))
        if (not parameters is None):
            _logger.debug('  parameters: {0}'.format(parameters))
        
        get_events = '{0}/me/calendarview?'.format(calendar_endpoint)
        
        if (not parameters is None):
            get_events = '{0}{1}'.format(get_events, parameters)
        
        r = self.make_api_call(cr,uid,'GET', get_events, token)
    
        if (r.status_code == requests.codes.unauthorized):
            _logger.debug('Leaving get_events.')
            return None
        _logger.debug('Response: {0}'.format(r.json()))
        _logger.debug('Leaving get_events.')
        
        return r.json()
    
    # Creates an event in the Calendar
    #   parameters:
    #     calendar_endpoint: string. The URL to the Calendar API endpoint (https://outlook.office365.com/api/v1.0)
    #     token: string. The access token 
    #     event_payload: string. A JSON representation of the new event.    
    def create_event(self,cr,uid,calendar_endpoint, token, event_payload):
        _logger.debug('Entering create_event.')
        _logger.debug('  calendar_endpoint: {0}'.format(calendar_endpoint))
        _logger.debug('  token: {0}'.format(token))
        _logger.debug('  event_payload: {0}'.format(event_payload))
                    
        create_event = '{0}/me/events'.format(calendar_endpoint)
        
        r = self.make_api_call(cr,uid,'POST', create_event, token, event_payload)
        
        _logger.debug('Response: {0}'.format(r.json()))
        _logger.debug('Leaving create_event.')
        
        return r.status_code

    # Deletes a single event
    #   parameters:
    #     calendar_endpoint: string. The URL to the Calendar API endpoint (https://outlook.office365.com/api/v1.0)
    #     token: string. The access token
    #     event_id: string. The ID of the event to delete.
    def delete_event(self,calendar_endpoint, token, event_id):
        _logger.debug('Entering delete_event.')
        _logger.debug('  calendar_endpoint: {0}'.format(calendar_endpoint))
        _logger.debug('  token: {0}'.format(token))
        _logger.debug('  event_id: {0}'.format(event_id))
                    
        delete_event = '{0}/Me/Events/{1}'.format(calendar_endpoint, event_id)
        
        r = self.make_api_call('DELETE', delete_event, token)
        
        _logger.debug('Leaving delete_event.')
        
        return r.status_code
    
    # Updates a single event
    #   parameters:
    #     calendar_endpoint: string. The URL to the Calendar API endpoint (https://outlook.office365.com/api/v1.0)
    #     token: string. The access token
    #     event_id: string. The ID of the event to update.    
    #     update_payload: string. A JSON representation of the properties to update.
    def update_event(self,calendar_endpoint, token, event_id, update_payload):
        _logger.debug('Entering update_event.')
        _logger.debug('  calendar_endpoint: {0}'.format(calendar_endpoint))
        _logger.debug('  token: {0}'.format(token))
        _logger.debug('  event_id: {0}'.format(event_id))
        _logger.debug('  update_payload: {0}'.format(update_payload))
                    
        update_event = '{0}/Me/Events/{1}'.format(calendar_endpoint, event_id)
        
        r = self.make_api_call('PATCH', update_event, token, update_payload)
    
        _logger.debug('Response: {0}'.format(r.json()))
        _logger.debug('Leaving update_event.')
        
        return r.status_code
        
