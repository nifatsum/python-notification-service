from src.api import fields, auth, Resource, reqparse, marshal, abort, orm

message_fields = {
    'message_id': fields.String,
    'title': fields.String,
    'text': fields.String,
    'recipient_type': fields.String,
    'recipient': fields.String,
    'state_id': fields.String,
    'error_message': fields.String,
    'create_date': fields.DateTime(dt_format="iso8601"),
    'update_date': fields.DateTime(dt_format="iso8601"),
    'address_id': fields.String,
    'user_id': fields.String,
    'notification_id': fields.String(attribute='notification'),
    'uri': fields.Url('message', absolute=True)
}
class MessageListAPI(Resource):
    decorators = [auth.login_required]

    def get(self, notification_id):
        try:
            with orm.db_session:
                n = orm.NotificationEntity[notification_id]
                i_list = [i.to_dict(with_collections=True) for i in n.messages.select()]
                return {
                    'notification_id': str(notification_id), 
                    'count': len(i_list),
                    'notifications': [marshal(i, message_fields) for i in i_list]}
        except orm.ObjectNotFound:
            abort(404)

class MessageAPI(Resource):
    """не обновляемый ресурс"""
    decorators = [auth.login_required]

    def get(self, message_id):
        with orm.db_session:
            i = orm.MesaageEntity.get(message_id=message_id)
            if not i:
                abort(404)
            return {'message': marshal(i.to_dict(with_collections=True), message_fields)}
