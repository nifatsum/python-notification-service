from app import e, fields, auth, Resource, reqparse, marshal, abort
from app.entities.user import UserEntity

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

user_reqparser = reqparse.RequestParser()
user_reqparser.add_argument('name', type=str, required=True, location='json')
user_reqparser.add_argument('email', type=str, default=None, location='json')
user_reqparser.add_argument('phone', type=str, default=None, location='json')

class UserListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = user_reqparser.copy()
        super().__init__()

    def get(self):
        with e.orm.db_session:
            i_list = [i.to_dict(with_collections=True) for i in UserEntity.select()]
            return {'users': [marshal(i, user_fields) for i in i_list] }
            # return [marshal(u, user_fields) for u in u_list]

    def post(self):
        args = self.reqparse.parse_args()
        with e.orm.db_session:
            name = args["name"]
            email = args["email"]
            phone = args["phone"]
            c = UserEntity.select(lambda u: u.name == name 
                                        or u.email == email 
                                        or u.phone == phone
                                ).count()
            if c > 0:
                abort(409) # TODO: заменить на abort_already_exists()
            i = UserEntity(name=name, email=email, phone=phone)
            return {'user': marshal(i.to_dict(with_collections=True), user_fields)}, 201
            # return marshal(u.to_dict(with_collections=True), user_fields), 201

class UserAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = user_reqparser.copy()
        super().__init__()

    def get(self, user_id):
        with e.orm.db_session:
            i = UserEntity.get(user_id=user_id)
            if not i:
                abort(404)
            return {'user': marshal(i.to_dict(with_collections=True), user_fields)}
            # return marshal(u.to_dict(with_collections=True), user_fields)

    # def put(self, user_id): pass # TODO: добавить обновление полейы (+связанные)