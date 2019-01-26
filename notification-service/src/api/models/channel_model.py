from src.api import fields, auth, Resource, reqparse, marshal, abort, orm

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
