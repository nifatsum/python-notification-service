from flask import Flask, jsonify, abort, make_response, request
from flask_restful import Api, Resource, reqparse, fields, marshal
from flask_httpauth import HTTPBasicAuth
import Domain.models as orm

orm.db.bind(provider="sqlite", filename="notifications.sqlite", create_db=True)
orm.db.generate_mapping(create_tables=True)
orm.DbInitor.seed()

app = Flask(__name__, static_url_path="")
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

# address_slim_fields = {
#     'address_id': fields.String,
#     'uri': fields.Url('address')
# }
user_fields = {
    'user_id': fields.String,
    'name': fields.String,
    'email': fields.String,
    'phone': fields.String,
    'create_date': fields.DateTime(dt_format="iso8601"),
    'update_date': fields.DateTime(dt_format="iso8601"),
    'addresses': fields.List(fields.String),
    'uri': fields.Url('user', absolute=True)
}

class UserListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True, location='json',
                                   help='No user name provided')
        self.reqparse.add_argument('email', type=str, default=None, location='json')
        self.reqparse.add_argument('phone', type=str, default=None, location='json')                                   
        super().__init__()

    def get(self):
        with orm.db_session:
            i_list = [i.to_dict(with_collections=True) for i in orm.UserEntity.select()]
            return {'users': [marshal(i, user_fields) for i in i_list] }
            # return [marshal(u, user_fields) for u in u_list]

    def post(self):
        args = self.reqparse.parse_args()
        with orm.db_session:
            i = orm.UserEntity(name=args["name"], email=args["email"], phone=args["phone"])
            return {'user': marshal(i.to_dict(with_collections=True), user_fields)}, 201
            # return marshal(u.to_dict(with_collections=True), user_fields), 201

class UserAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True, location='json',
                                   help='No user name provided')
        # self.reqparse.add_argument('email', type=str, default=None, location='json')
        # self.reqparse.add_argument('phone', type=str, default=None, location='json')
        super().__init__()

    def get(self, user_id):
        with orm.db_session:
            i = orm.UserEntity.get(user_id=user_id)
            if not i:
                abort(404)
            return {'user': marshal(i.to_dict(with_collections=True), user_fields)}
            # return marshal(u.to_dict(with_collections=True), user_fields)

    # def put(self, user_id):
    #     pass # TODO: добавить обновление полейы (+связанные)


# -----------------------------------------------------------------

address_fields = {
    'address_id': fields.String,
    'type_id': fields.String,
    'recipient': fields.String,
    'user_id': fields.String(attribute='user'),
    'create_date': fields.DateTime(dt_format="iso8601"),
    'update_date': fields.DateTime(dt_format="iso8601"),
    'channels': fields.List(fields.String),
    'notifications': fields.List(fields.String),
    'uri': fields.Url('address', absolute=True)
}
class AddressListAPI(Resource):
    decorators = [auth.login_required]
    # def __init__(self):
    #     # self.reqparse = reqparse.RequestParser()
    #     # self.reqparse.add_argument('type_id', type=str, required=True, location='json',
    #     #                 help='No address type_id provided')
    #     # self.reqparse.add_argument('recipient', type=str, required=True, location='json',
    #     #                 help='No address recipient provided')
    #     super(AddressListAPI, self).__init__()

    def get(self):
        with orm.db_session:
            i_list = [i.to_dict(with_collections=True) for i in orm.AddressEntity.select()]
            return {'addresses': [marshal(i, address_fields) for i in i_list]}

class AddressAPI(Resource):
    decorators = [auth.login_required]

    def get(self, address_id):
        with orm.db_session:
            i = orm.AddressEntity.get(address_id=address_id)
            if not i:
                abort(404)
            return {'address': marshal(i.to_dict(with_collections=True), address_fields)}

    # def put(self, address_id):
    #     pass # TODO: добавить изменение адреса НЕ ПРИВЯЗАННОГО к пользователю!

# -----------------------------------------------------------------

channel_fields = {
    'channel_id': fields.String,
    'name': fields.String,
    'description': fields.String,
    'create_date': fields.DateTime(dt_format="iso8601"),
    'update_date': fields.DateTime(dt_format="iso8601"),
    'addresses': fields.List(fields.String),
    'notifications': fields.List(fields.String),
    'uri': fields.Url('channel', absolute=True)
}
class ChannelListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True, location='json',
                        help='No channel name provided')
        self.reqparse.add_argument('description', type=str, location='json',
                        help='No channel description provided')
        super().__init__()

    def get(self):
        with orm.db_session:
            i_list = [i.to_dict(with_collections=True) for i in orm.ChannelEntity.select()]
            return {'channels': [marshal(i, channel_fields) for i in i_list]}

    def post(self):
        args = self.reqparse.parse_args()
        with orm.db_session:
            i = orm.ChannelEntity(name=args["name"], description=args["description"])
            return {'channel': marshal(i.to_dict(with_collections=True), channel_fields)}, 201

class ChannelAPI(Resource):
    decorators = [auth.login_required]

    def get(self, channel_id):
        with orm.db_session:
            i = orm.ChannelEntity.get(channel_id=channel_id)
            if not i:
                abort(404)
            return {'channel': marshal(i.to_dict(with_collections=True), channel_fields)}

# -----------------------------------------------------------------

notification_fields = {
    'notification_id': fields.String,
    'title': fields.String(),
    'text': fields.String,
    'create_date': fields.DateTime(dt_format="iso8601"),
    #'update_date': fields.DateTime(dt_format="iso8601"),
    'addresses': fields.List(fields.String),
    'channel_id': fields.String(attribute='channel'),
    'uri': fields.Url('notification', absolute=True)
}
class NotificationListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('title', type=str, required=True, location='json',
                        help='No notification title provided')
        self.reqparse.add_argument('text', type=str, required=True, location='json',
                        help='No notification text provided')
        # TODO: добавить возможность указывать address_ids при создании уведомления
        super().__init__()

    def get(self, channel_id):
        try:
            print('channel_id: {}'.format(channel_id))
            with orm.db_session:
                ch = orm.ChannelEntity[channel_id]
                i_list = [i.to_dict(with_collections=True) for i in ch.notifications.select()]
                return {
                    'channel_id': str(channel_id), 
                    'notifications': [marshal(i, notification_fields) for i in i_list]}
        except orm.ObjectNotFound:
            abort(404)

    def post(self, channel_id):
        try:
            args = self.reqparse.parse_args()
            with orm.db_session:
                ch = orm.ChannelEntity[channel_id]
                i = ch.create_notification(title=args['title'], text=args['text'])
                return {'notification': marshal(i.to_dict(with_collections=True), notification_fields)}, 201
        except orm.EntityCreationError as e:
            abort({'message': e.message}, 500)
        except orm.ObjectNotFound as e:
            abort(404)

class NotificationAPI(Resource):
    """не обновляемый ресурс, (только пересоздание от существующего Channel)"""
    decorators = [auth.login_required]

    def get(self, notification_id):
        with orm.db_session:
            i = orm.NotificationEntity.get(notification_id=notification_id)
            if not i:
                abort(404)
            return {'notification': marshal(i.to_dict(with_collections=True), notification_fields)}


# -----------------------------------------------------------------
api.add_resource(UserListAPI, '/api/v1.0/users', endpoint='users')
api.add_resource(UserAPI, '/api/v1.0/users/<uuid:user_id>', endpoint='user')

api.add_resource(AddressListAPI, '/api/v1.0/addresses', endpoint='addresses')
api.add_resource(AddressAPI, '/api/v1.0/addresses/<uuid:address_id>', endpoint='address')

api.add_resource(ChannelListAPI, '/api/v1.0/channels', endpoint='channels')
api.add_resource(ChannelAPI, '/api/v1.0/channels/<uuid:channel_id>', endpoint='channel')

api.add_resource(NotificationListAPI, '/api/v1.0/channels/<uuid:channel_id>/notifications', endpoint='notifications')
api.add_resource(NotificationAPI, '/api/v1.0/notifications/<uuid:notification_id>', endpoint='notification')

# TODO: '/api/v1.0/channels/<uuid:channel_id>/addresses'
# TODO: в сущностях где есть адреса - выводить адреса подробно, а не только address_id

if __name__ == '__main__':
    app.run(debug=True)
