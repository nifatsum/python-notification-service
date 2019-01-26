from datetime import datetime
from src.api import fields, auth, Resource, reqparse, marshal, abort, orm

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