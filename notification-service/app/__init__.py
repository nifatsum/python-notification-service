
from flask import Flask, jsonify, abort, make_response, request
from flask_restful import Api, Resource, reqparse, fields, marshal
from flask_httpauth import HTTPBasicAuth
from datetime import datetime

#from app.entities import orm
import app.entities as e
from app.entities.db_initor import DbInitor

from app.models import *

app = Flask(__name__, static_url_path="")

app.config.update(dict(
    PONY = {
        'provider': 'sqlite',
        'filename': 'notifications.sqlite',
        'create_db': True
    }
))

e.db.bind(**app.config['PONY'])
e.db.generate_mapping(create_tables=True)
DbInitor.seed()


api = Api(app)
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == 'admin':
        return '12345678'
    return None

# @auth.verify_password
# def verify_password(u, p):
#     print('verify_password: [{0}], [{1}]'.format(u, p))
#     return True

@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)

api.add_resource(UserListAPI, '/api/v1.0/users', endpoint='users')
api.add_resource(UserAPI, '/api/v1.0/users/<uuid:user_id>', endpoint='user')

api.add_resource(AddressListAPI, '/api/v1.0/channels/<uuid:channel_id>/addresses', endpoint='addresses')
api.add_resource(AddressAPI, '/api/v1.0/addresses/<uuid:address_id>', endpoint='address')

api.add_resource(ChannelListAPI, '/api/v1.0/channels', endpoint='channels')
api.add_resource(ChannelAPI, '/api/v1.0/channels/<uuid:channel_id>', endpoint='channel')

api.add_resource(NotificationListAPI, '/api/v1.0/channels/<uuid:channel_id>/notifications', endpoint='notifications')
api.add_resource(NotificationAPI, '/api/v1.0/notifications/<uuid:notification_id>', endpoint='notification')

# TODO: в сущностях где есть адреса - выводить адреса подробно, а не только address_id (проблема с цикличностью)

class IndexApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('list', type=list, location='json')
        super().__init__()

    def get(self):
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Salam'
            }

    def post(self):
        args = self.reqparse.parse_args()
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'args': args
            }
api.add_resource(IndexApi, '/api/v1.0/', endpoint='index')


