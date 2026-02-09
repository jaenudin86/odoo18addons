# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Ayana KP (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import json
import logging
from odoo import http
from odoo.http import request
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class RestApi(http.Controller):
    """This is a controller which is used to generate responses based on the
    api requests"""

    def _cors_headers(self):
        """Generate CORS headers for cross-origin requests"""
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, api-key, login, password, db',
            'Access-Control-Max-Age': '86400',
            'Content-Type': 'application/json'
        }

    def _make_json_response(self, data, status=200):
        """Create a proper JSON response with CORS headers"""
        headers = self._cors_headers()
        if isinstance(data, dict):
            body = json.dumps(data, ensure_ascii=False, default=str)
        else:
            body = data
        return request.make_response(body, headers=headers, status=status)

    def _make_error_response(self, message, status=400):
        """Create a standardized error response"""
        return self._make_json_response({
            'status': 'error',
            'message': message
        }, status=status)

    def auth_api_key(self, api_key):
        """This function is used to authenticate the api-key when sending a
        request"""
        if not api_key:
            return {
                'success': False,
                'message': 'No API Key Provided'
            }
        
        user_id = request.env['res.users'].sudo().search([('api_key', '=', api_key)], limit=1)
        
        if user_id:
            return {
                'success': True,
                'user_id': user_id.id
            }
        else:
            return {
                'success': False,
                'message': 'Invalid API Key'
            }

    def _serialize_value(self, value):
        """Serialize special Python types to JSON-compatible formats"""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except:
                return str(value)
        elif isinstance(value, tuple):
            # Handle Many2one fields (id, name)
            return {'id': value[0], 'name': value[1]} if len(value) == 2 else list(value)
        return value

    def _serialize_record(self, record):
        """Serialize a single record"""
        for key, value in record.items():
            record[key] = self._serialize_value(value)
        return record

    def generate_response(self, method, model, rec_id):
        """This function is used to generate the response based on the type
        of request and the parameters given"""
        try:
            option = request.env['connection.api'].search(
                [('model_id', '=', model)], limit=1)
            
            if not option:
                return self._make_error_response("No API configuration found for this model", 404)
            
            model_name = option.model_id.model
            
            # Parse request data
            data = {}
            if method != 'DELETE':
                try:
                    if request.httprequest.data:
                        data = json.loads(request.httprequest.data)
                except json.JSONDecodeError:
                    return self._make_error_response("Invalid JSON Data", 400)
            
            fields = data.get('fields', []) if data else []
            
            if not fields and method not in ['DELETE']:
                return self._make_error_response("No fields selected for the model", 400)
            
            # GET Method
            if method == 'GET':
                if not option.is_get:
                    return self._make_error_response("GET method not allowed", 405)
                
                domain = [('id', '=', rec_id)] if rec_id != 0 else []
                records = request.env[model_name].sudo().search_read(
                    domain=domain,
                    fields=fields
                )
                
                # Serialize records
                for record in records:
                    self._serialize_record(record)
                
                return self._make_json_response({
                    'status': 'success',
                    'count': len(records),
                    'records': records
                })
            
            # POST Method
            elif method == 'POST':
                if not option.is_post:
                    return self._make_error_response("POST method not allowed", 405)
                
                if 'values' not in data:
                    return self._make_error_response("Missing 'values' in request data", 400)
                
                new_resource = request.env[model_name].sudo().create(data['values'])
                
                records = request.env[model_name].sudo().search_read(
                    domain=[('id', '=', new_resource.id)],
                    fields=fields
                )
                
                for record in records:
                    self._serialize_record(record)
                
                return self._make_json_response({
                    'status': 'success',
                    'message': 'Resource created successfully',
                    'record': records[0] if records else {}
                }, 201)
            
            # PUT Method
            elif method == 'PUT':
                if not option.is_put:
                    return self._make_error_response("PUT method not allowed", 405)
                
                if rec_id == 0:
                    return self._make_error_response("No ID provided", 400)
                
                if 'values' not in data:
                    return self._make_error_response("Missing 'values' in request data", 400)
                
                resource = request.env[model_name].sudo().browse(int(rec_id))
                
                if not resource.exists():
                    return self._make_error_response("Resource not found", 404)
                
                resource.write(data['values'])
                
                records = request.env[model_name].sudo().search_read(
                    domain=[('id', '=', resource.id)],
                    fields=fields
                )
                
                for record in records:
                    self._serialize_record(record)
                
                return self._make_json_response({
                    'status': 'success',
                    'message': 'Resource updated successfully',
                    'record': records[0] if records else {}
                })
            
            # DELETE Method
            elif method == 'DELETE':
                if not option.is_delete:
                    return self._make_error_response("DELETE method not allowed", 405)
                
                if rec_id == 0:
                    return self._make_error_response("No ID provided", 400)
                
                resource = request.env[model_name].sudo().browse(int(rec_id))
                
                if not resource.exists():
                    return self._make_error_response("Resource not found", 404)
                
                deleted_info = {
                    'id': resource.id,
                    'display_name': resource.display_name
                }
                
                resource.unlink()
                
                return self._make_json_response({
                    'status': 'success',
                    'message': 'Resource deleted successfully',
                    'deleted': deleted_info
                })
        
        except Exception as e:
            _logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return self._make_error_response(f"Internal server error: {str(e)}", 500)

    @http.route(['/send_request'], type='http',
                auth='none',
                methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], csrf=False)
    def fetch_data(self, **kw):
        """This controller will be called when sending a request to the
        specified url, and it will authenticate the api-key and then will
        generate the result"""
        
        # Handle OPTIONS request for CORS preflight
        if request.httprequest.method == 'OPTIONS':
            return request.make_response('', headers=self._cors_headers())
        
        http_method = request.httprequest.method
        
        # Get credentials
        api_key = request.httprequest.headers.get('api-key')
        username = request.httprequest.headers.get('login')
        password = request.httprequest.headers.get('password')
        model = kw.get('model')
        
        # Validate model
        if not model:
            return self._make_error_response("Model parameter is required", 400)
        
        try:
            # Authenticate user
            if username and password:
                credential = {
                    'login': username,
                    'password': password,
                    'type': 'password'
                }
                request.session.authenticate(request.session.db, credential)
            
            # Check if model exists
            model_id = request.env['ir.model'].sudo().search([('model', '=', model)], limit=1)
            
            if not model_id:
                return self._make_error_response(
                    "Invalid model, check spelling or the related module may not be installed",
                    404
                )
            
            # Authenticate API key
            auth_result = self.auth_api_key(api_key)
            
            if not auth_result['success']:
                return self._make_error_response(auth_result['message'], 401)
            
            # Get record ID
            rec_id = int(kw.get('Id', 0))
            
            # Generate response
            result = self.generate_response(http_method, model_id.id, rec_id)
            return result
            
        except Exception as e:
            _logger.error(f"Error in fetch_data: {str(e)}", exc_info=True)
            return self._make_error_response(f"Authentication or processing error: {str(e)}", 500)

    @http.route(['/odoo_connect'], type="http", auth="none", csrf=False,
                methods=['GET', 'POST', 'OPTIONS'])
    def odoo_connect(self, **kw):
        """This is the controller which initializes the api transaction by
        generating the api-key for specific user and database"""
        
        # Handle OPTIONS request for CORS preflight
        if request.httprequest.method == 'OPTIONS':
            return request.make_response('', headers=self._cors_headers())
        
        username = request.httprequest.headers.get('login')
        password = request.httprequest.headers.get('password')
        db = request.httprequest.headers.get('db')
        
        if not all([username, password, db]):
            return self._make_error_response(
                "Missing required headers: login, password, or db",
                400
            )
        
        try:
            request.session.update(http.get_default_session(), db=db)
            credential = {
                'login': username,
                'password': password,
                'type': 'password'
            }
            
            auth = request.session.authenticate(db, credential)
            user = request.env['res.users'].browse(auth['uid'])
            api_key = request.env.user.generate_api(username)
            
            return self._make_json_response({
                'status': 'success',
                'message': 'Authentication successful',
                'user': user.name,
                'user_id': user.id,
                'api_key': api_key
            })
            
        except Exception as e:
            _logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return self._make_error_response("Wrong login credentials", 401)