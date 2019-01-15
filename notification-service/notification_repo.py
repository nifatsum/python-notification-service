from decimal import Decimal
from datetime import datetime
from pony.orm import *
import uuid

db = Database()
db.bind(provider='sqlite', filename='notifications.sqlite', create_db=True, timeout=500)

class TinyArgValidator():
    @staticmethod
    def isNullOrEmpty(arg):
        if arg is None:
            return True
        if isinstance(arg, str) and len(arg) == 0:
            return True
        return False
    @staticmethod
    def notEmptyStr(arg, arg_name):
        """if {arg} is null or empty, raise "ValueError" with specified {arg_name}"""
        if TinyArgValidator.isNullOrEmpty(arg):
            raise ValueError('you must specify "{}"'.format(arg_name if arg_name is not None else ''))

class User(db.Entity):
    _table_ = "User"
    name = PrimaryKey(str, column='Name')
    email = Optional(str, column="Email", nullable=True)
    phone = Optional(str, column="Phone", nullable=True)
    create_date = Required(datetime, column='CreateDate', default=datetime.utcnow())
    addresses = Set('Address')

    @staticmethod
    def create(name, email=None, phone=None):
        TinyArgValidator.notEmptyStr(name, 'user name')
        if email is None and phone is None:
            raise ValueError('you must specify an email or phone')

        new_user = User(name=name, email=email, phone=phone)
        return new_user
    
    def __str__(self):
        rec = '' if self.email is None else self.email
        if self.phone is not None:
            rec += ('' if len(rec) == 0 else ', ') + self.phone
        return '{0} | [{1}] | {2}'.format(self.name, rec, self.create_date.isoformat())

allowed_address_types = ['email', 'phone']
class Address(db.Entity):
    _table_ = "Address"
    id = PrimaryKey(uuid.UUID, default=uuid.uuid4, column='AddressId')
    type_id = Required(str, column="TypeId")
    recipiend = Required(str, column="Recipient")
    user = Optional(lambda: User, column="UserIdentificator")
    channel = Optional(lambda: NotificationChannel)

    @staticmethod
    def create(type_id, recipient, user=None):
        if type_id is None or type_id not in allowed_address_types:
            raise ValueError('allowed types is {}'.format(allowed_address_types))

        TinyArgValidator.notEmptyStr(recipient, 'Address.recipient')

        new_address = Address(type_id=type_id, recipient=recipient, user=user)
        return new_address


class NotificationChannel(db.Entity):
    _table_ = "NotificationChannel"
    id = PrimaryKey(str, column='ChannelId')
    title = Required(str, column="Title")
    addresses = Set(lambda: Address)

    @staticmethod
    def create(id, title):
        TinyArgValidator.notEmptyStr(id, 'Channel.id')
        TinyArgValidator.notEmptyStr(title, 'Channel.title')
        new_channel = NotificationChannel(id=id, title=title)
        return new_channel

class NotificationRepo:
    def __init__(self, data_base=None, debug=False):
        self.db = data_base if data_base is not None else db
        self.debug = debug
        set_sql_debug(self.debug)
        self.db.generate_mapping(create_tables=True)
        self.seed()

    def seed(self):
        pass

    @db_session
    def get_user(self, name):
        user = User.get(name=name)
        return user

    @db_session
    def get_users(self):
        users = select(u for u in User).order_by(User.create_date)
        return list(users)

    @db_session
    def add_user(self, name, email=None, phone=None):
        user = self.get_user(name)
        if user is None:
            print('  create new user.')
            user = User.create(name=name, email=email, phone=phone)
        return user

if __name__ == '__main__':
    r = NotificationRepo(db, False)
    #r.add_user('Gena', email='some@mail.com')

    print('users:')
    try:
        u1 = None
        u1 = r.add_user(name='u1',phone='555')
        #with db_session:
        #    User.create(name='u1',email='some@email.com',phone='333')
        #    u1 = User.get(name='u1')
        print(u1)


        u11 = None
        u11 = r.add_user(name='u11',phone='555')
        print(u11)

        u2 = None
        with db_session:
            User.create(name='u2',phone='444')
            u2 = User.get(name='u2')
        print(u2)
        u3 = None
        with db_session:
            u3 = User.create(name='u3',email='some222@email.com')
        print(u3)
    except Exception as e:
        print('{0} - {1}'.format(type(e), e))

    print('users:')
    u_list = r.get_users()
    for u in u_list:
        print('  {}'.format(u))

# надо наружу отдавать симметричные "простые" классы

