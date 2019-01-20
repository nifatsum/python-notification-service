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
        if isinstance(obj, db.Entity):
            q = json.dumps(obj.to_dict(), default=EntityHelper.json_convert_default)
            return q
        return json.dumps(obj)

    @staticmethod
    def to_string(o):
        s = "[{0}]:".format(type(o).__name__)
        for k, v in o.__dict__.items():
            s += "\n  - {0} ({1}): {2}".format(k, type(v).__name__, 
                                        v.isoformat() if isinstance(v, datetime) else v)
        return s.rstrip()

    @staticmethod
    def to_json(o, indent=4):
        x = isinstance(o, db.Entity)
        return json.dumps(
            obj= o.to_dict() if x else o.__dict__, 
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
    def __init__(self, name, user_id=None,
                email=None, phone=None, 
                create_date=datetime.utcnow(),
                address_ids = [],
                notification_ids = []):
        self.user_id = user_id if user_id else uuid.uuid4()
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
        self.notification_ids = []
        if notification_ids and len(notification_ids) > 0:
            self.notification_ids.extend(notification_ids)

    def get_addresses(self):
        l = []
        if self.email and len(self.email) > 0:
            l.append(Address(type_id="email", recipient=self.email, user_id=self.user_id))
        if self.phone and len(self.phone) > 0:
            l.append(Address(type_id="phone", recipient=self.phone, user_id=self.user_id))
        self.address_ids.extend(x.address_id for x in l if x.address_id not in self.address_ids)
        return l

class UserEntity(db.Entity):
    _table_ = "User"
    user_id = PrimaryKey(uuid.UUID, column="UserId", default=uuid.uuid4)
    name = Required(str, column="Name")
    email = Optional(str, column="Email", nullable=True)
    phone = Optional(str, column="Phone", nullable=True)
    create_date = Required(datetime, column="CreateDate", default=datetime.utcnow())
    addresses = Set(lambda: AddressEntity)
    notifications = Set(lambda: NotificationEntity)

    @classmethod
    def create(cls, name, 
            user_id=None, 
            email=None, phone=None, 
            create_date=datetime.utcnow()):
        try:
            TinyArgValidator.notEmptyStr(name, "user name")
            if email is None and phone is None:
                raise ValueError('you must specify an "email" or "phone"')
            if not user_id:
                user_id = uuid.uuid4()
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
                    address_ids=[a.address_id for a in self.addresses],
                    notification_ids=[n.notification_id for n in self.notifications])

#----------------------------------------------------------

allowed_address_types = ["email", "phone"]
class Address(BasePrimitive):
    def __init__(self, type_id, recipient, 
                address_id=None,
                create_date=datetime.utcnow(),
                user_id=None, channel_id=None):
        self.address_id = address_id if address_id else uuid.uuid4()
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
            address_id=None,
            create_date=datetime.utcnow(), 
            user=None, channel=None):
        try:
            if type_id not in allowed_address_types:
                raise ValueError("allowed types is {}".format(allowed_address_types))
            TinyArgValidator.notEmptyStr(recipient, "Address.recipient")
            if not address_id:
                address_id = uuid.uuid4()
            new_address = AddressEntity(address_id=address_id,
                                        type_id=type_id, 
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
    def __init__(self, name, title, channel_id=None, 
                address_ids=[], notification_ids = []):
        self.channel_id = channel_id if channel_id else uuid.uuid4()
        TinyArgValidator.notEmptyStr(name, "Channel.name")
        self.name = name
        TinyArgValidator.notEmptyStr(title, "Channel.title")
        self.title = title
        
        self.address_ids = [] 
        if address_ids and len(address_ids) > 0:
             self.address_ids.extend(address_ids)
        
        self.notification_ids = []
        if notification_ids and len(notification_ids) > 0:
            self.notification_ids.extend(notification_ids)

class ChannelEntity(db.Entity):
    _table_ = "Channel"
    channel_id = PrimaryKey(uuid.UUID, column="ChannelId", default=uuid.uuid4)
    name = Required(str, column="Name")
    title = Optional(str, column="Title", nullable=True)
    create_date = Required(datetime, column="CreateDate", default=datetime.utcnow())
    addresses = Set(lambda: AddressEntity)
    notifications = Set(lambda: NotificationEntity)

    @classmethod
    def create(cls, name, 
            title=None, 
            create_date=datetime.utcnow(), 
            channel_id=None):
        try:
            TinyArgValidator.notEmptyStr(name, "Channel.id")
            TinyArgValidator.notEmptyStr(title, "Channel.title")
            if not channel_id:
                channel_id = uuid.uuid4()
            new_channel = ChannelEntity(channel_id=channel_id, 
                                        name=name, 
                                        title=title, 
                                        create_date=create_date)
            return new_channel
        except Exception as e:
            raise EntityCreationError("({0}) {1}".format(cls.__name__, e), e)

    def map(self):
        return Channel(channel_id=self.channel_id, 
                    name=self.name,
                    title=self.title, 
                    address_ids=[a.address_id for a in self.addresses],
                    notification_ids=[n.notification_id for n in self.notifications])

#-------------------------------------------------------------

class Notification(BasePrimitive):
    def __init__(self, title, text, 
            notification_id=None, 
            create_date=datetime.utcnow(), 
            user_id=None, channel_id=None):
        self.notification_id = notification_id if notification_id else uuid.uuid4()
        self.title = title
        self.text = text
        self.create_date = create_date
        if user_id and not isinstance(user_id, uuid.UUID):
            raise EntityCreationError("{0}.ctor() - UUID expected in user_id".format(self.__class__.__name__))
        self.user_id = user_id
        if user_id and not isinstance(channel_id, uuid.UUID):
            raise EntityCreationError("{0}.ctor() - UUID expected in channel_id".format(self.__class__.__name__))
        self.channel_id = channel_id

class NotificationEntity(db.Entity):
    _table_ = "Notification"
    notification_id = PrimaryKey(uuid.UUID, column="NotificationId", default=uuid.uuid4)
    title = Required(str, column="Title")
    text = Required(str, column="Text")
    create_date = Required(datetime, column="CreateDate", default=datetime.utcnow())
    user = Optional(lambda: UserEntity, column="UserId", nullable=True) # TODO: заменить на адрес
    channel = Optional(lambda: ChannelEntity, column="ChannelId", nullable=True)

    @classmethod
    def create(title, text, 
            notification_id=None, 
            create_date=datetime.utcnow(), 
            user=None, channel=None):
        if not user and not channel:
            raise EntityCreationError("NotificationEntity.create() - user or chnannel required")
        TinyArgValidator.notEmptyStr(title, 'Notification.title')
        TinyArgValidator.notEmptyStr(text, 'Notification.text')
        if not notification_id:
            notification_id=uuid.uuid4()
        return NotificationEntity(notification_id=notification_id,
                                title=title,
                                text=text,
                                create_date=create_date,
                                user=user,
                                channel=channel)

    def map(self):
        return Notification(notification_id=self.notification_id,
                            title=self.title,
                            text=self.text,
                            create_date=self.create_date,
                            user_id=self.user.user_id if self.user else None,
                            channel_id=self.channel.channel_id if self.channel else None)

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
        for i in range(1, 3):
            u_name = 'some_man_{0}'.format(i)

            if len(self.get_users(name=u_name)) > 0:
                continue

            u = self.add_user(name=u_name, 
                            email='user{0}@email.com'.format(i), 
                            phone='7922{0}'.format(str(i)*7))
            alist = u.get_addresses()
            for a in alist:
                self.add_address(type_id=a.type_id, 
                                recipient=a.recipient,
                                address_id=a.address_id, 
                                create_date=a.create_date,
                                user=u)

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
    def get_users(self, name=None):
        q = select(u for u in UserEntity)
        if name:
            q.where(lambda u: u.name == name)
        q = q.order_by(UserEntity.create_date)
        return [u.map() for u in q]

    @db_session # TODO: возможно этот метод не нужен
    def add_user(self, name, email=None, phone=None):
        """no exist check"""
        user = UserEntity.create(name=name, email=email, phone=phone)
        return user.map()

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

    @db_session
    def get_addresses(self, type_id=None, user_id=None):
        q = select(a for a in AddressEntity)

        if type_id:
            q = q.where(lambda a: a.type_id == type_id)

        if user_id:
            q = q.where(lambda a: a.user.user_id == user_id)

        q = q.order_by(AddressEntity.create_date)
        return [i.map() for i in q]

    @db_session
    def get_address(self, address_id):
        i = AddressEntity.get(address_id=address_id)
        return i.map() if i else None

    @db_session
    def add_address(self, type_id, recipient, address_id=uuid.uuid4(),
                create_date=datetime.utcnow(), user=None, channel=None):
        """no exist check"""
        u = UserEntity.get(user_id=user.user_id) if user else None
        c = ChannelEntity.get(channel_id=channel.channel_id) if channel else None
        addr = AddressEntity.create(address_id=address_id, type_id=type_id, 
                                recipient=recipient, create_date=create_date,
                                user=u, channel=c)
        return addr.map()
    # TODO: add methods for other entities
    # TODO: addres & channel must user many-to-many relation!

if __name__ == "__main__":
    pass
