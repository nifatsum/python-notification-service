from flask import Flask, jsonify, abort, make_response, request
from flask_restful import Api, Resource, reqparse, fields, marshal
from flask_httpauth import HTTPBasicAuth
from datetime import datetime
import src.entities as orm

orm.db.bind(provider="sqlite", filename="./assets/notifications.sqlite", create_db=True)
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
    # TODO: стоил выдавать ссылки на ресурс?
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
            n = args["name"]
            e = args["email"]
            p = args["phone"]
            print(n, e, p)
            c = orm.UserEntity.select(lambda u: u.name == n 
                                        or u.email == e 
                                        or u.phone == p
                                ).count()
            if c > 0:
                abort(409) # TODO: заменить на abort_already_exists()
            i = orm.UserEntity(name=n, email=e, phone=p)
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

    # def put(self, user_id): pass # TODO: добавить обновление полейы (+связанные)

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
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('type_id', type=str, required=True, location='json',
                        help='is empty or invalid (allowed: {0})'.format(orm.allowed_address_types), 
                        choices=tuple(orm.allowed_address_types))
        self.reqparse.add_argument('recipient', type=str, location='json')
        self.reqparse.add_argument('user_id', type=orm.uuid.UUID, location='json')
        super(AddressListAPI, self).__init__()

    def get(self, channel_id):
        try:
            with orm.db_session:
                ch = orm.ChannelEntity[channel_id]
                i_list = [i.to_dict(with_collections=True) for i in ch.addresses.select()]
                return {
                    'channel_id': str(channel_id),
                    'count': len(i_list),
                    'addresses': [marshal(i, address_fields) for i in i_list]
                    }
        except orm.ObjectNotFound:
            abort(404)

    def post(self, channel_id):
        """создаем адрес внутри указанного канала"""
        try:
            args = self.reqparse.parse_args()
            with orm.db_session:
                # проверяем существование канала
                ch = orm.ChannelEntity[channel_id]

                # TODO: добавить возвожность добавлять адрес указывая список address_ids

                rec = None
                t = args['type_id']
                u_id = args['user_id']
                u = None
                if u_id:
                    # проверяем существование пользователя, если указан user_id
                    u = orm.UserEntity.get(user_id=u_id)
                    if not u:
                        abort(404, {'message': 'user not found'})
                    # получаем у пользователя адрес указанного типа 
                    a = u.get_address_by_type(t)
                    if a:
                        rec = a.recipient
                    else:
                        abort(400, {'message': 'user address not found'})
                else:
                    # иначе берем получателя из body
                    rec = args['recipient']

                # проверяем не добавлен ли уже этот адрес в канал
                # NOTE: для проверки наличия элемента в коллекции лучше юзать Set.count()
                c = ch.addresses.select(lambda a: a.type_id == t 
                                        and a.recipient == rec 
                                        and (u is None or a.user == u)
                                ).count()
                if c > 0:
                    abort(409, {'message': 'already exists'})

                i = ch.addresses.create(type_id=t, recipient=rec, user=u)

                res = i.to_dict(with_collections=True)
                return {
                    'channel_id': str(channel_id),
                    # TODO: нужно ли здесь добавить uri на указанный channel ??
                    'addresses': marshal(res, address_fields)
                    }, 201
        except orm.EntityCreationError as e:
            abort(500, {'message': e.message})
        except orm.ObjectNotFound as e:
            abort(404)


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
            n = args["name"]
            ex_i = orm.ChannelEntity.get(name=n)
            if ex_i:
                abort(409) # channel already exists
            i = orm.ChannelEntity(name=n, description=args["description"])
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
    'external_id': fields.String,
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
        self.reqparse.add_argument('external_id', type=str, location='json')
        # TODO: добавить возможность указывать address_ids при создании уведомления
        super().__init__()

    def get(self, channel_id):
        try:
            with orm.db_session:
                ch = orm.ChannelEntity[channel_id]
                i_list = [i.to_dict(with_collections=True) for i in ch.notifications.select()]
                return {
                    'channel_id': str(channel_id), 
                    'count': len(i_list),
                    'notifications': [marshal(i, notification_fields) for i in i_list]}
        except orm.ObjectNotFound:
            abort(404)

    def post(self, channel_id):
        """создаем уведомление внутри указанного канала"""
        try:
            #raise orm.EntityCreationError('my test messssssageeeeeeeee')
            args = self.reqparse.parse_args()
            with orm.db_session:
                ch = orm.ChannelEntity[channel_id]

                external_id = args['external_id']
                if external_id:
                    exist_n = ch.notifications.select(lambda n: n.external_id == external_id).first()
                    if exist_n:
                        # TODO: заменить abort(409) на кастомный метод, возвращающий json помимо StatusCode
                        abort(409, 'already exists') 

                t = args['title']
                s = args['text']
                #i = orm.NotificationEntity(external_id=external_id, title=t, text=s, channel=ch)
                i = ch.notifications.create(external_id=external_id, title=t, text=s)

                res = i.to_dict(with_collections=True)
                return {'notification': marshal(res, notification_fields)}, 201
        except orm.EntityCreationError as e:
            abort(500, {'message': e.message})
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

if __name__ == '__main__':
    app.run(debug=True)
