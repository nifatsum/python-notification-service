from src.api import fields, auth, Resource, reqparse, marshal, abort, orm, Response

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
            # return [marshal(u, user_fields) for u in u_list] ???

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
        # self.reqparse = reqparse.RequestParser()
        # self.reqparse.add_argument('name', type=str, required=True, location='json',
        #                            help='No user name provided')
        # self.reqparse.add_argument('email', type=str, default=None, location='json')
        # self.reqparse.add_argument('phone', type=str, default=None, location='json')
        super().__init__()

    def get(self, user_id):
        with orm.db_session:
            i = orm.UserEntity.get(user_id=user_id)
            if not i:
                abort(404)
            return {'user': marshal(i.to_dict(with_collections=True), user_fields)}

    def delete(self, user_id):
        with orm.db_session:
            i = orm.UserEntity.get(user_id=user_id)
            if not i:
                abort(404)
            i.delete()
            return Response(status=200)


    # def put(self, user_id): pass # TODO: добавить обновление полейы (+связанные)
