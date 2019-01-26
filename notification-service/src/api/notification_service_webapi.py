from datetime import datetime
from src.api import (jsonify, abort, make_response, request,
                    Resource, reqparse, fields, marshal, 
                    Flask, Api, HTTPBasicAuth, auth, orm)

from src.api.user_model import UserAPI, UserListAPI
from src.api.address_model import AddressAPI, AddressListAPI
from src.api.channel_model import ChannelAPI, ChannelListAPI

orm.db.bind(provider="sqlite", filename="./../assets/notifications.sqlite", create_db=True)
orm.db.generate_mapping(create_tables=True)
orm.DbInitor.seed()

app = Flask(__name__, static_url_path="")
api = Api(app)

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
