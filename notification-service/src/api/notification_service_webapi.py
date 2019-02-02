import logging, json
from datetime import datetime
from src.api import (jsonify, abort, make_response, request, swagger,
                    Resource, reqparse, fields, marshal, 
                    Flask, Api, HTTPBasicAuth, auth, orm)

from src.api.models import *
from src.logger import LoggerProxy

orm.db.bind(provider="sqlite", filename="./../assets/notifications.sqlite", create_db=True)
orm.db.generate_mapping(create_tables=True)
orm.DbInitor.seed()

app = Flask(__name__, static_url_path="")
api = Api(app)
api = swagger.docs(api, apiVersion='1.0')


class LoggerMiddleware(object):
    def __init__(self, app, logger):
        self.app = app
        self.__logger = logger

    def __call__(self, environ, start_response):
        # self.__logger.info(str(environ.keys()))
        self.__logger.info("{0} {1}{2} {3}", 
                        environ.get('REQUEST_METHOD'), 
                        environ.get('HTTP_HOST'), environ.get('PATH_INFO'), 
                        environ.get('SERVER_PROTOCOL'))
        #self.__logger.info("QUERY_STRING:{0} REMOTE_ADDR:{0}", environ['QUERY_STRING'], environ['REMOTE_ADDR'])
        # ["wsgi.version", "wsgi.url_scheme", "wsgi.input", "wsgi.errors", "wsgi.multithread", 
        # "wsgi.multiprocess", "wsgi.run_once", "werkzeug.server.shutdown", "SERVER_SOFTWARE", 
        # "REQUEST_METHOD", "SCRIPT_NAME", "PATH_INFO", "QUERY_STRING", "REMOTE_ADDR", "REMOTE_PORT", 
        # "SERVER_NAME", "SERVER_PORT", "SERVER_PROTOCOL", "HTTP_AUTHORIZATION", "HTTP_CACHE_CONTROL", 
        # "HTTP_POSTMAN_TOKEN", "HTTP_USER_AGENT", "HTTP_ACCEPT", "HTTP_HOST", "HTTP_ACCEPT_ENCODING", 
        # "HTTP_CONNECTION", "werkzeug.request"]
        #self.__logger.info(json.dumps([k for k in environ.keys()]))
        # s = ''
        # for k,v in environ.items():
        #     s += '{0}: {1}\n'.format(k, v)
        # self.__logger.info(s.rstrip())
        return self.app(environ, start_response)

app.wsgi_app = LoggerMiddleware(app.wsgi_app, LoggerProxy('Flask'))
log = logging.getLogger('werkzeug')
log.disabled = True

@app.after_request
def add_header(r):
    # отключаем кеширование в браузере
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# @auth.get_password
# def get_password(username):
#     if username == 'admin':
#         return '12345678'
#     return None

@auth.verify_password
def verify_password(u, p):
    if not u or not p:
        return False
    # print('verify_password: [{0}], [{1}]'.format(u, p))
    # return False
    with orm.db_session:
        u = orm.UserEntity.get(name=u)
        pass_with_salt = '{0}{1}'.format(p, u.user_id if u else None)
        # print('pass_with_salt:', pass_with_salt)
        if not u or not u.verify_password(pass_with_salt):
            return False
    return True

@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)

api.add_resource(UserListAPI, '/api/v1.0/users', endpoint='users')
api.add_resource(UserAPI, '/api/v1.0/users/<uuid:user_id>', endpoint='user')

api.add_resource(AddressListAPI, '/api/v1.0/channels/<uuid:channel_id>/addresses', endpoint='addresses')
api.add_resource(AddressAPI, '/api/v1.0/addresses/<uuid:address_id>', endpoint='address')

api.add_resource(ChannelListAPI, '/api/v1.0/channels', endpoint='channels')
api.add_resource(ChannelAPI, '/api/v1.0/channels/<uuid:channel_id>', endpoint='channel')

api.add_resource(NotificationListAPI, '/api/v1.0/channels/<uuid:channel_id>/notifications', endpoint='notifications')
api.add_resource(NotificationAPI, '/api/v1.0/notifications/<uuid:notification_id>', endpoint='notification')

api.add_resource(MessageListAPI, '/api/v1.0/notifications/<uuid:notification_id>/messages', endpoint='messages')
api.add_resource(MessageAPI, '/api/v1.0/messages/<uuid:message_id>', endpoint='message')

api.add_resource(IndexApi, '/api/v1.0/', endpoint='index')

# TODO: в сущностях где есть адреса - выводить адреса подробно, а не только address_id (проблема с цикличностью)

# if __name__ == '__main__':
#     app.run(debug=True)
