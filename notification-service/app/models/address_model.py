from app import e, fields, auth, Resource, reqparse, marshal, abort
from app.entities.address import AddressEntity, allowed_address_types
from app.entities.user import UserEntity
from app.entities.channel import ChannelEntity

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

address_reqparser = reqparse.RequestParser()
address_reqparser.add_argument('type_id', type=str, required=True, location='json',
                help='is empty or invalid (allowed: {0})'.format(allowed_address_types), 
                choices=tuple(allowed_address_types))
address_reqparser.add_argument('recipient', type=str, location='json')
address_reqparser.add_argument('user_id', type=e.uuid.UUID, location='json')

class AddressListAPI(Resource):
    decorators = [auth.login_required]
    def __init__(self):
        self.reqparse = address_reqparser.copy()
        super(AddressListAPI, self).__init__()

    def get(self, channel_id):
        try:
            with e.orm.db_session:
                ch = ChannelEntity[channel_id]
                i_list = [i.to_dict(with_collections=True) for i in ch.addresses.select()]
                return {
                    'channel_id': str(channel_id),
                    'count': len(i_list),
                    'addresses': [marshal(i, address_fields) for i in i_list]
                    }
        except e.orm.ObjectNotFound:
            abort(404)

    def post(self, channel_id):
        """создаем адрес внутри указанного канала"""
        try:
            args = self.reqparse.parse_args()
            with e.orm.db_session:
                # проверяем существование канала
                ch = ChannelEntity[channel_id]

                # TODO: добавить возвожность добавлять адрес указывая список address_ids

                rec = None
                t = args['type_id']
                u_id = args['user_id']
                u = None
                if u_id:
                    # проверяем существование пользователя, если указан user_id
                    u = UserEntity.get(user_id=u_id)
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
        except e.EntityCreationError as ex:
            abort(500, {'message': ex.message})
        except e.orm.ObjectNotFound as ex:
            abort(404)


class AddressAPI(Resource):
    decorators = [auth.login_required]

    def get(self, address_id):
        with e.orm.db_session:
            i = AddressEntity.get(address_id=address_id)
            if not i:
                abort(404)
            return {'address': marshal(i.to_dict(with_collections=True), address_fields)}

    # def put(self, address_id):
    #     pass # TODO: добавить изменение адреса НЕ ПРИВЯЗАННОГО к пользователю!