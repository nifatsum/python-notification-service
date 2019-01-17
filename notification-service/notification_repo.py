from decimal import Decimal
from datetime import datetime
from pony.orm import *
import uuid
import json

db = Database()
db.bind(provider="sqlite", filename="notifications.sqlite", create_db=True)

class EntityCreationError(ValueError):
    def __init__(self, message, inner=None, *args, **kwargs):
        self.message = message
        self.inner = inner
        ValueError.__init__(self, message, *args, **kwargs)

class EntityHelper:
    @staticmethod
    def json_convert_default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        return json.dumps(obj)

    @staticmethod
    def to_string(o):
        s = "[{0}]:".format(type(o).__name__)
        for k, v in o.__dict__.items():
            s += "\n  - {0}({1}): {2}".format(k, type(v).__name__, 
                                        v.isoformat() if isinstance(v, datetime) else v)
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
                .format(arg_name if arg_name else ''))

class BasePrimitive:
    def __init__(self):
        pass
    def __str__(self):
        return EntityHelper.to_string(o=self)
    def to_json(self, indent=None):
        return EntityHelper.to_json(o=self, indent=indent)

#----------------------------------------------------------

class User(BasePrimitive):
    def __init__(self, user_id, name, 
                email=None, phone=None, 
                create_date=datetime.utcnow(),
                address_ids = []):
        self.user_id = user_id
        TinyArgValidator.notEmptyStr(name, "user name")
        self.name = name
        if email is None and phone is None:
                raise EntityCreationError('you must specify an "email" or "phone"')
        self.email = email
        self.phone = phone
        self.create_date = create_date
        self.address_ids = [] # список идетификаторов
        if address_ids and len(address_ids) > 0:
            self.address_ids.extend(address_ids)

class UserEntity(db.Entity):
    _table_ = "User"
    user_id = PrimaryKey(uuid.UUID, column="UserId", default=uuid.uuid4)
    name = Required(str, column="Name")
    email = Optional(str, column="Email", nullable=True)
    phone = Optional(str, column="Phone", nullable=True)
    create_date = Required(datetime, column="CreateDate", default=datetime.utcnow())
    addresses = Set(lambda: AddressEntity)

    @classmethod
    def create(cls, name, 
            user_id=uuid.uuid4(), 
            email=None, phone=None, 
            create_date=datetime.utcnow()):
        try:
            TinyArgValidator.notEmptyStr(name, "user name")
            if email is None and phone is None:
                raise ValueError('you must specify an "email" or "phone"')
            new_user = UserEntity(user_id=user_id,
                                name=name, 
                                email=email, 
                                phone=phone, 
                                create_date=create_date)
            return new_user
        except Exception as e:
            raise EntityCreationError("({0}) {1}".format(cls.__name__, e), e)

    def map(self):
        # в address_ids передаем только идентификаторы
        return User(user_id = self.user_id, 
                    name=self.name, 
                    email=self.email, 
                    phone=self.phone,
                    create_date=self.create_date,
                    address_ids=[a.address_id for a in self.addresses])

#----------------------------------------------------------

allowed_address_types = ["email", "phone"]
class Address(BasePrimitive):
    def __init__(self, address_id, type_id, 
                recipient, create_date=datetime.utcnow(),
                user_id=None, channel_id=None):
        self.address_id = address_id
        if type_id not in allowed_address_types:
            raise ValueError("allowed types is {}".format(allowed_address_types))
        self.type_id = type_id
        TinyArgValidator.notEmptyStr(recipient, "Address.recipient")
        self.recipient = recipient
        self.create_date = create_date
        # далее только идетификаторы! НЕ сущности!
        self.user_id = user_id
        self.channel_id = channel_id

class AddressEntity(db.Entity):
    _table_ = "Address"
    address_id = PrimaryKey(uuid.UUID, column="AddressId", default=uuid.uuid4)
    type_id = Required(str, column="TypeId")
    recipient = Required(str, column="Recipient")
    create_date = Required(datetime, column="CreateDate", default=datetime.utcnow())
    user = Optional(lambda: UserEntity, column="UserId")
    channel = Optional(lambda: ChannelEntity, column="ChannelId")

    @classmethod
    def create(cls, type_id, recipient, 
            address_id=uuid.uuid4(),
            create_date=datetime.utcnow(), 
            user=None, channel=None):
        try:
            if type_id not in allowed_address_types:
                raise ValueError("allowed types is {}".format(allowed_address_types))
            TinyArgValidator.notEmptyStr(recipient, "Address.recipient")
            new_address = AddressEntity(type_id=type_id, 
                                        recipient=recipient, 
                                        create_date=create_date, 
                                        user=user, 
                                        channel=channel)
            return new_address
        except Exception as e:
            raise EntityCreationError("({0}) {1}".format(cls.__name__, e), e)

    def map(self):
        return Address(address_id=self.address_id, 
                        type_id=self.type_id, 
                        recipient=self.recipient,
                        create_date=self.create_date,
                        user_id=self.user.user_id if self.user else None, 
                        channel_id=self.channel.channel_id if self.channel else None)

#----------------------------------------------------------

class Channel(BasePrimitive):
    def __init__(self, channel_id, name, title, address_ids=[]):
        self.channel_id = channel_id
        TinyArgValidator.notEmptyStr(name, "Channel.name")
        self.name = name
        TinyArgValidator.notEmptyStr(title, "Channel.title")
        self.title = title
        self.address_ids = [] 
        if address_ids and len(address_ids) > 0:
             self.address_ids.extend(address_ids)

class ChannelEntity(db.Entity):
    _table_ = "Channel"
    channel_id = PrimaryKey(uuid.UUID, column="ChannelId", default=uuid.uuid4)
    name = Required(str, column="Name")
    title = Optional(str, column="Title", nullable=True)
    addresses = Set(lambda: AddressEntity)

    @classmethod
    def create(cls, name, title=None, channel_id=uuid.uuid4()):
        try:
            TinyArgValidator.notEmptyStr(name, "Channel.id")
            TinyArgValidator.notEmptyStr(title, "Channel.title")
            new_channel = ChannelEntity(channel_id=channel_id, name=name, title=title)
            return new_channel
        except Exception as e:
            raise EntityCreationError("({0}) {1}".format(cls.__name__, e), e)

    def map(self):
        return Channel(channel_id=self.channel_id, 
                        name=self.name,
                        title=self.title, 
                        address_ids=[a.address_id for a in self.addresses])

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
        self.db = data_base if data_base else db

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

    # TODO: приукрутить логгер
    def log_info(self, msg, *args, **kwargs):
        if len(args) > 0:
            msg = msg.format(*args)
        else:
            msg = msg.format(**kwargs)
        print('{0} [INFO] {1}: {2}'.format(datetime.utcnow.isoformat(), 
                                            self.__class__.__name__, 
                                            msg))
    #-------------------------------------------------------

    @db_session
    def get_user(self, user_id):
        user = UserEntity.get(user_id=user_id)
        return user.map() if user else None

    @db_session
    def get_users(self):
        users = select(u for u in UserEntity).order_by(UserEntity.create_date)
        return [u.map() for u in users]

    @db_session
    def add_user(self, name, email=None, phone=None):
        """no exist check"""
        user = UserEntity.create(name=name, email=email, phone=phone)
        return user.map()
        # user = self.get_user(name)
        # if user is None:
        #     user = UserEntity.create(name=name, email=email, phone=phone).map()
        # else:
        #     self.log_info('user with {0} is aready exists', name)
        # return user

    @db_session
    def save_user(self, u):
        # TODO: добавить обновление полей для существующей записи
        """void method. expects User class instance. check entity exists.\n
        HAS NO UPDATE exist item (only add to context) !!!
        """
        if not isinstance(u, User):
            raise EntityCreationError("Repo.save_user(arg) - expects User class instance.")
        e = self.get_user(user_id=u.user_id)
        if e is None:
            UserEntity.create(user_id=u.user_id,
                                name=u.name, 
                                email=u.email, 
                                phone=u.phone, 
                                create_date=u.create_date)
        else:
            self.log_info("user [{0}] is already exists", u.user_id)

    #-------------------------------------------------------
    # TODO: add methods for other entities
    # TODO: addres & channel must user many-to-many relation!
