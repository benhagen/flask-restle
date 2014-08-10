from flask import json, request, current_app
from flask.views import View
from werkzeug.wrappers import BaseResponse
from werkzeug.routing import BaseConverter
import arrow

# GET = Fetch
# POST = Create new
# PUT = Total update
# PATCH = Partial update
# DELETE = Delete


class API(View):
	method = None
	decorators = []
	response_headers = {}
	response_status = None
	response_mimetype = "application/json"
	response_status_defaults = {
		"delete": 200,
		"get": 200,
		"patch": 200,
		"post": 200,
		"put": 201
	}


	def dispatch_init(self, *args, **kwargs):
		""" This method should be overriden to do things like input validation, normalization, etc.
			It is executed after some generic request validation, but before the method is executed. 
			Should return """
		return (args, kwargs)

	def dispatch_request(self, *args, **kwargs):
		self.method = request.method.lower()

		# We only take JSON here sonny
		if request.data and request.mimetype != 'application/json':
			raise api_error("Request payload mimetype must be 'application/json'", status_code=415)

		# Do the MethodView type calling of methods
		method = getattr(self, self.method, None)
		# Sanity check the method, and check if method exists in class
		if self.method not in ["get", "put", "post", "delete", "patch"] or not method:
			raise api_error("HTTP method is not supported", status_code=405) # This should return a list of acceptable methods ... hrm

		args, kwargs = self.dispatch_init(*args, **kwargs)

		output = method(*args, **kwargs)

		# If the function made a legit response for us already, just go with the flow
		if type(output) == type(BaseResponse()):
			return output

		# Otherwise, wrap everything in JSON
		if output is not None:
			output = json.dumps(output, indent=4, sort_keys=True)
		return self.build_response(output)

	def build_response(self, body=None):
		""" Builds the response object """
		if not body:
			mimetype = None
		else:
			mimetype = self.response_mimetype
		# If no response_status has been set, be lazy and fetch from default for method
		status = self.response_status or self.response_status_defaults[request.method.lower()]
		# Override 200 when no body is present
		if status == 200 and not body:
			status = 204
		return current_app.response_class(body, status=status, mimetype=mimetype, headers=self.response_headers)


class api_error(Exception):
	## Common Errors
	# 401 - Unauthorized
	# 402 - Payment required
	# 403 - Forbidden
	# 404 - Not Found
	# 405 - Method not allowed
	# 406 - Not acceptable
	# 415 - Unsupported media type

	status_code = 400

	def __init__(self, message, status_code=None, payload=None):
		Exception.__init__(self)
		self.message = message
		if status_code is not None:
			self.status_code = status_code
		self.payload = payload

	def to_dict(self):
		rv = dict(self.payload or ())
		rv['error_message'] = self.message
		return rv

	def response(self):
		return current_app.response_class(json.dumps(self.to_dict(), indent=4, sort_keys=True), status=self.status_code, mimetype='application/json')


#
# Helper function to automagically register some normal recipes
#
def register_api(blueprint, view, endpoint, url, pk='id', pk_type='int'):
	view_func = view.as_view(endpoint)
	# GET - List
	blueprint.add_url_rule(url, defaults={pk: None}, view_func=view_func, methods=['GET'])
	# POST - Create
	blueprint.add_url_rule(url, view_func=view_func, methods=['POST'])
	# GET - Fetch one
	# PUT - Update
	# DELETE - Delete
	blueprint.add_url_rule('%s<%s:%s>' % (url, pk_type, pk), view_func=view_func, methods=['GET', 'PUT', 'DELETE'])


#
# Extend the default JSON encoder
# Add the following to your app:
#	app.json_encoder = CustomJSONEncoder
#	app.json_decoder = CustomJSONDecoder

class CustomJSONEncoder(json.JSONEncoder):
	""" Adds a few features to the vanilla encoder (its a lie) """

	def __init__(self, *args, **kwargs):
		json.JSONEncoder.__init__(self, *args, **kwargs)

	def default(self, obj):
		# Override the default serializer if an object has a "json_serializer" function already defined
		json_serializer = getattr(obj, "json_serializer", None)
		if callable(json_serializer):
			return obj.json_serializer()
		# Handle sets as lists
		if type(obj) is set:
			return list(obj)
		# Convert Arrow objects to isoformat
		if type(obj) is arrow.arrow.Arrow:
			return obj.isoformat()
		return json.JSONEncoder.default(self, obj)



# Make some stuff serializable
class JsonEncoder(json.JSONEncoder):
	def default(self, obj):
		json_serializer = getattr(obj, "json_serializer", None)
		if callable(json_serializer):
		    return json_serializer()
		return json.JSONEncoder.default(self, obj)




class CustomJSONDecoder(json.JSONDecoder):
	""" Adds a few features to the vanilla decoder """

	def __init__(self, *args, **kwargs):
		kwargs.setdefault('object_hook', self.object_hook)
		json.JSONDecoder.__init__(self, *args, **kwargs)

	def object_hook(self, obj):
		return obj


#
# Some helpful converters for URL matching
# http://werkzeug.pocoo.org/docs/routing/#custom-converters

class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

class EmailConverter(BaseConverter):
	def __init__(self, url_map):
		super(EmailConverter, self).__init__(url_map)
		self.regex = "[^@ ]+@[^@ ]+\.[^@ ]+"

class IPv4Converter(BaseConverter):
	def __init__(self, url_map):
		super(IPv4Converter, self).__init__(url_map)
		self.regex = "(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])"

class CidrConverter(BaseConverter):
	def __init__(self, url_map):
		super(CidrConverter, self).__init__(url_map)
		self.regex = "(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/([1-2]\d|3[0-2]|\d))"

def extend_converters(app):
	app.url_map.converters['regex'] = RegexConverter
	app.url_map.converters['email'] = EmailConverter
	app.url_map.converters['ip'] = IPv4Converter
	app.url_map.converters['cidr'] = CidrConverter
	return app

def restle(app):
	extend_converters(app)
	app.json_encoder = CustomJSONEncoder
	app.json_decoder = CustomJSONDecoder

	@app.errorhandler(api_error)
	def handle_invalid_usage(error):
		return error.response()
