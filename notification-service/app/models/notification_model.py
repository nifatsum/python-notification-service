from app import e, fields, auth, Resource, reqparse, marshal, abort
from app.entities.notification import NotificationEntity
from app.entities.channel import ChannelEntity

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

notification_reqparser = reqparse.RequestParser()
notification_reqparser.add_argument('title', type=str, required=True, location='json')
notification_reqparser.add_argument('text', type=str, required=True, location='json')
notification_reqparser.add_argument('external_id', type=str, location='json')

class NotificationListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = notification_reqparser.copy()
        # TODO: добавить возможность указывать address_ids при создании уведомления
        super().__init__()

    def get(self, channel_id):
        try:
            with e.orm.db_session:
                ch = ChannelEntity[channel_id]
                i_list = [i.to_dict(with_collections=True) for i in ch.notifications.select()]
                return {
                    'channel_id': str(channel_id), 
                    'count': len(i_list),
                    'notifications': [marshal(i, notification_fields) for i in i_list]}
        except e.orm.ObjectNotFound:
            abort(404)

    def post(self, channel_id):
        """создаем уведомление внутри указанного канала"""
        try:
            #raise orm.EntityCreationError('my test messssssageeeeeeeee')
            args = self.reqparse.parse_args()
            with e.orm.db_session:
                ch = ChannelEntity[channel_id]

                external_id = args['external_id']
                if external_id:
                    exist_n = ch.notifications.select(lambda n: n.external_id == external_id).first()
                    if exist_n:
                        # TODO: заменить abort(409) на кастомный метод, возвращающий json помимо StatusCode
                        abort(409) 

                t = args['title']
                s = args['text']
                #i = orm.NotificationEntity(external_id=external_id, title=t, text=s, channel=ch)
                i = ch.notifications.create(external_id=external_id, title=t, text=s)

                res = i.to_dict(with_collections=True)
                return {'notification': marshal(res, notification_fields)}, 201
        except e.EntityCreationError as ex:
            abort(500, {'message': ex.message})
        except e.orm.ObjectNotFound:
            abort(404)

class NotificationAPI(Resource):
    """не обновляемый ресурс, (только пересоздание от существующего Channel)"""
    decorators = [auth.login_required]

    def get(self, notification_id):
        with e.orm.db_session:
            i = NotificationEntity.get(notification_id=notification_id)
            if not i:
                abort(404)
            return {'notification': marshal(i.to_dict(with_collections=True), notification_fields)}