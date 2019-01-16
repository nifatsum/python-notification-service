from decimal import Decimal
from datetime import datetime
from pony.orm import *
import uuid
import json

db = Database()
db.bind(provider='sqlite', filename='notifications.sqlite', create_db=True, timeout=500)

class EntityCreationError(ValueError):
    def __init__(self, message, inner=None, *args, **kwargs):
        self.message = message
        self.inner = inner
        ValueError.__init__(self, message, *args, **kwargs)

class EntityHelper:
    @staticmethod
    def json_convert_default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, uuid.UUID):
            return str(o)
        return json.dumps(o)

    @staticmethod
    def to_string(o):
        s = '[{0}]:'.format(type(o).__name__)
        for k, v in o.__dict__.items():
            s += '\n  - {0}({1}): {2}'.format(k, type(v).__name__, v)
        return s.rstrip()

    @staticmethod
    def to_json(o, indent=None):
        return json.dumps(
            obj=o.__dict__, 
            default=EntityHelper.json_convert_default, 
            indent=indent)

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
            raise ValueError('you must specify "{}"'
                .format(arg_name if arg_name is not None else ''))

class BasePrimitive:
    def __init__(self):
        pass

    def __str__(self):
        return EntityHelper.to_string(o=self)

    def to_json(self, indent=None):
        return EntityHelper.to_json(o=self, indent=indent)

#----------------------------------------------------------

class User(BasePrimitive):
    def __init__(self, name, 
                email=None, phone=None, 
                create_date=datetime.utcnow(), 
                addresses=[]):
        TinyArgValidator.notEmptyStr(name, 'user name')
        self.name = name
        if email is None and phone is None:
                raise EntityCreationError('you must specify an "email" or "phone"')
        self.email = email
        self.phone = phone
        self.create_date = create_date

        self.addresses = [] 
        if addresses is not None and len(addresses) > 0:
             self.addresses.extend(addresses)
        #if len(self.addresses) > 0 and not isinstance(self.addresses[0], )


class UserEntity(db.Entity):
    _table_ = "User"
    name = PrimaryKey(str, column='Name')
    email = Optional(str, column="Email", nullable=True)
    phone = Optional(str, column="Phone", nullable=True)
    create_date = Required(datetime, column='CreateDate', default=datetime.utcnow())
    addresses = Set(lambda: AddressEntity)

    @staticmethod
    def create(name, email=None, phone=None):
        try:
            TinyArgValidator.notEmptyStr(name, 'user name')
            if email is None and phone is None:
                raise ValueError('you must specify an "email" or "phone"')

            new_user = UserEntity(name=name, email=email, phone=phone)
            return new_user
        except Exception as e:
            raise EntityCreationError('(UserEntity) ' + str(e), e)

    def map(self):
        return User(name=self.name, 
                    email=self.email, phone=self.phone,
                    create_date=self.create_date,
                    addresses=[a.map() for a in self.addresses])

    # def __str__(self):
    #     rec = '' if self.email is None else self.email
    #     if self.phone is not None:
    #         rec += ('' if len(rec) == 0 else ', ') + self.phone
    #     return '{0} | [{1}] | {2}'.format(self.name, rec, self.create_date.isoformat())

#----------------------------------------------------------

allowed_address_types = ['email', 'phone']
class Address(BasePrimitive):
    def __init__(self, id, type_id, recipient,
                user=None, channel=None):
        self.id = id
        if type_id is None or type_id not in allowed_address_types:
            raise ValueError('allowed types is {}'.format(allowed_address_types))
        self.type_id = type_id
        TinyArgValidator.notEmptyStr(recipient, 'Address.recipient')
        self.recipient = recipient
        # TODO: check arg type
        self.user = user
        self.channel = channel


class AddressEntity(db.Entity):
    _table_ = "Address"
    id = PrimaryKey(uuid.UUID, default=uuid.uuid4, column='AddressId')
    type_id = Required(str, column="TypeId")
    recipient = Required(str, column="Recipient")
    user = Optional(lambda: UserEntity, column="UserIdentificator")
    channel = Optional(lambda: ChannelEntity)

    @staticmethod
    def create(type_id, recipient, user=None):
        try:
            if type_id is None or type_id not in allowed_address_types:
                raise ValueError('allowed types is {}'.format(allowed_address_types))
            TinyArgValidator.notEmptyStr(recipient, 'Address.recipient')
            new_address = AddressEntity(type_id=type_id, recipient=recipient, user=user)
            return new_address
        except Exception as e:
            raise EntityCreationError('(AddressEntity) ' + str(e), e)

    def map(self):
        return Address(id=self.id, type_id=self.type_id, recipient=self.recipient,
                    user=self.user.map(), channel=self.channel.map())

#----------------------------------------------------------

class Channel(BasePrimitive):
    def __init__(self, id, title, addresses=[]):
        TinyArgValidator.notEmptyStr(id, 'Channel.id')
        self.id = id
        TinyArgValidator.notEmptyStr(title, 'Channel.title')
        self.title = title
        self.addresses = [] 
        if addresses is not None and len(addresses) > 0:
             self.addresses.extend(addresses)

class ChannelEntity(db.Entity):
    _table_ = "NotificationChannel"
    id = PrimaryKey(str, column='ChannelId')
    title = Required(str, column="Title")
    addresses = Set(lambda: AddressEntity)

    @staticmethod
    def create(id, title):
        try:
            TinyArgValidator.notEmptyStr(id, 'Channel.id')
            TinyArgValidator.notEmptyStr(title, 'Channel.title')
            new_channel = ChannelEntity(id=id, title=title)
            return new_channel
        except Exception as e:
            raise EntityCreationError('(AddressEntity) ' + str(e), e)

    def map(self):
        return Channel(id=self.id, title=self.title, 
                        addresses=[a.map() for a in self.addresses])

#-------------------------------------------------------------
class RepoFactory:
    rcount = 0
    @staticmethod
    def get():
        need_create_tables=True
        if RepoFactory.rcount > 0:
            need_create_tables=False
        RepoFactory.rcount += 1
        return NotificationRepo(create_tables=need_create_tables)

class NotificationRepo:
    def __init__(self, data_base=None, create_tables=False, debug=False):
        self.db = data_base if data_base is not None else db

        if create_tables:
            self.db.generate_mapping(create_tables=create_tables)

        self.debug = debug
        set_sql_debug(self.debug)

        self.seed()

    def seed(self):
        self.add_user(
                name='some_man', 
                email='some@email.com', 
                phone='777')

    #-------------------------------------------------------

    @db_session
    def get_user(self, name):
        user = UserEntity.get(name=name)
        return user.map()

    @db_session
    def get_users(self):
        users = select(u for u in UserEntity).order_by(UserEntity.create_date)
        return [u.map() for u in users]

    @db_session
    def add_user(self, name, email=None, phone=None):
        user = self.get_user(name)
        if user is None:
            print('  create new user.')
            user = UserEntity.create(name=name, email=email, phone=phone).map()
        return user

    @db_session
    def save_user(self, u):
        """void method. expects User class instance."""
        if not isinstance(u, User):
            raise EntityCreationError('Repo.save_user(arg) - expects User class instance.')
        UserEntity.create(name=u.name, email=u.email, phone=u.phone)

    #-------------------------------------------------------
    # TODO: add methods for other entities
