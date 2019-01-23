from decimal import Decimal
import datetime as dt
import uuid
import json
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, OrmError, Set, ObjectNotFound

db = Database()
default_bus_message_sender = None

class DbInitor: # TODO: придумать нормальное название класса
    @staticmethod
    @db_session
    def seed():
        def_channel = ChannelEntity.get(name='default')
        if not def_channel:
            # юзаем фиксированный uuid для default канала
            ch_id = uuid.UUID('c64f941d-de0c-484d-8451-98747bbcc831')
            def_channel = ChannelEntity(channel_id=ch_id, name='default', description='default channel')

        for i in range(1, 3):
            u_name = 'some_man_{0}'.format(i)
            u = UserEntity.get(name=u_name)
            if u:
                continue

            e = 'user{0}@email.com'.format(i)
            p = '7922{0}'.format(str(i)*7)
            UserEntity(name=u_name, email=e, phone=p)

class EntityCreationError(OrmError):
    def __init__(self, message, inner=None, *args, **kwargs):
        self.message = message
        self.inner = inner
        super().__init__(message, *args, **kwargs)

class EntityHelper:
    def_dumps_indent = 4
    dumps_indent = 4

    def_to_dict_with_collections = True
    to_dict_with_collections = True

    to_dict_related_objects = False
    def_to_dict_related_objects = False

    def_max_relation_depth = 1
    max_relation_depth = None
    relation_depth = None

    converter = None

    @staticmethod
    def default_json_converter(obj):
        ind = EntityHelper.dumps_indent or EntityHelper.def_dumps_indent
        convr = EntityHelper.converter or EntityHelper.default_json_converter

        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return json.dumps(dict(obj), default=convr, indent=ind)
        if hasattr(obj, '__iter__'): 
            return json.dumps(list(obj), default=convr, indent=ind)
        if isinstance(obj, db.Entity):
            with_coll = EntityHelper.to_dict_with_collections or EntityHelper.def_to_dict_with_collections
            rel_obj = EntityHelper.def_to_dict_related_objects

            if EntityHelper.relation_depth is not None and EntityHelper.max_relation_depth:
                EntityHelper.relation_depth += 1
                if EntityHelper.relation_depth >= EntityHelper.max_relation_depth:
                    rel_obj = False
                else:
                    rel_obj = EntityHelper.to_dict_related_objects or EntityHelper.def_to_dict_related_objects

            _d = obj.to_dict(related_objects=rel_obj, with_collections=with_coll)
            _s = json.dumps(_d, default=convr, indent=ind)
            #, ensure_ascii=False
            return _s #.replace('\\"', '"').replace('\\n', '\n')
        return json.dumps(obj, default=convr, indent=ind)

    @staticmethod
    def to_json(obj, indent=None, converter=None, with_collections=None, 
            related_objects=None, depth=None):
        try:
            if not indent:
                indent = EntityHelper.def_dumps_indent
            EntityHelper.dumps_indent = indent

            if not converter:
                converter = EntityHelper.default_json_converter
            EntityHelper.converter = converter

            if not with_collections:
                with_collections = EntityHelper.def_to_dict_with_collections
            EntityHelper.to_dict_with_collections = with_collections

            if not related_objects:
                related_objects = EntityHelper.def_to_dict_related_objects
            EntityHelper.to_dict_related_objects = related_objects

            if not depth:
                depth = EntityHelper.def_max_relation_depth
            EntityHelper.max_relation_depth = depth
            EntityHelper.relation_depth = 0

            is_entity = isinstance(obj, db.Entity)
            o_dict = None
            if is_entity:
                o_dict = obj.to_dict(
                    with_collections=with_collections, 
                    related_objects=related_objects)
            else:
                o_dict = obj.__dict__
            s = json.dumps(obj=o_dict, default=converter, indent=indent)
            return s
        finally:
            EntityHelper.max_relation_depth = None
            EntityHelper.relation_depth = None

    @staticmethod
    def to_string(o):
        s = "[{0}]:".format(type(o).__name__)
        for k, v in o.__dict__.items():
            is_date = isinstance(v, (dt.datetime, dt.date))
            s += "\n  - {0} ({1}): {2}".format(k, type(v).__name__, 
                                        v.isoformat() if is_date else v)
        return s.rstrip()

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

#----------------------------------------------------------

class UserEntity(db.Entity):
    _table_ = "User"
    # TODO: set user_id as bigint
    user_id = PrimaryKey(uuid.UUID, column="UserId", default=uuid.uuid4) 
    password_hash = Optional(str, column="PasswordHash", nullable=True, max_len=64)
    name = Required(str, column="Name", unique=True, max_len=64)
    email = Optional(str, column="Email", nullable=True, max_len=64)
    phone = Optional(str, column="Phone", nullable=True, max_len=32)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())
    addresses = Set(lambda: AddressEntity)

    def before_insert(self):
        if len(self.email or '') == 0 and len(self.phone or '') == 0:
            m = '({0})you must specify an "email" or "phone"'
            raise EntityCreationError(m.format(self.__class__.__name__))

    def after_insert(self):
        """создаем адреса и добавляем их в default канал"""
        a_list = []
        if self.email and len(self.email) > 0:
            a_list.append(self.addresses.create(type_id="email", recipient=self.email))
        if self.phone and len(self.phone) > 0:
            a_list.append(self.addresses.create(type_id="phone", recipient=self.phone))

        def_channel = ChannelEntity.get(name='default')
        if def_channel:
            def_channel.addresses.add(a_list)

    def get_address_by_type(self, type_id):
        i = self.addresses.select(lambda a: a.type_id == type_id).first()
        return i

    def update_email(self, new_email):
        # TODO: *
        raise EntityCreationError("not implemented")

    def update_phone(self, new_phone):
        # TODO: *
        raise EntityCreationError("not implemented")

#----------------------------------------------------------

allowed_address_types = ["email", "phone"]
class AddressEntity(db.Entity):
    _table_ = "Address"
    address_id = PrimaryKey(uuid.UUID, column="AddressId", default=uuid.uuid4)
    type_id = Required(str, column="TypeId", max_len=16)
    recipient = Required(str, column="Recipient", max_len=64)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())
    user = Optional(lambda: UserEntity, column="UserId")
    channels = Set(lambda: ChannelEntity)
    notifications = Set(lambda: NotificationEntity)

    def before_insert(self):
        if self.type_id not in allowed_address_types:
            m = "({0}) allowed types is {1}"
            raise EntityCreationError(m.format(self.__class__.__name__, 
                                allowed_address_types))

    def update_recipient(self, new_recipient):
        raise OrmError('update_recipient - is not implemented')
        # TODO: add validation
        self.recipient = new_recipient
        # TODO: update user credentionals if need
        self.update_date = dt.datetime.utcnow()

#----------------------------------------------------------

class ChannelEntity(db.Entity):
    _table_ = "Channel"
    channel_id = PrimaryKey(uuid.UUID, column="ChannelId", default=uuid.uuid4)
    name = Required(str, column="Name", unique=True, max_len=64)
    description = Optional(str, column="Description", nullable=True, max_len=512)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())
    addresses = Set(lambda: AddressEntity)
    notifications = Set(lambda: NotificationEntity)

#-------------------------------------------------------------

class NotificationEntity(db.Entity):
    """
    всегда создается от имени какого-либо канала (по умолчанию от default)\n
    можно непосредственно указать список адресов, иначе берутся адреса канала
    """
    _table_ = "Notification"
    notification_id = PrimaryKey(uuid.UUID, column="NotificationId", default=uuid.uuid4)
    external_id = Required(str, column="ExternalId", unique=True, max_len=64)
    title = Required(str, column="Title", max_len=128)
    text = Required(str, column="Text", max_len=1024)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    addresses = Set(lambda: AddressEntity)
    channel = Required(lambda: ChannelEntity, column="ChannelId")
    messages = Set(lambda: MesaageEntity)

    def before_insert(self):
        if len(self.external_id or '') == 0:
            self.external_id = str(self.notification_id)
        print('before_insert(notification)')
        print('self.channel: ', self.channel)
        print('self.addresses: ', self.addresses)
        if self.channel and len(self.addresses) == 0:
            if self.channel.addresses.count() > 0:
                for a in self.channel.addresses.select():
                    self.addresses.add(a)

    # def after_insert(self):
    #     # TODO: здесь для каждого адреса нужно создать MesaageEntity
    #     pasraise EntityCreationError("not implemented")

#-------------------------------------------------------------

allowed_message_state_ids = ["Created", "Processing", "Sent", "Error"]
class MesaageEntity(db.Entity):
    _table_ = "NotificationMesaage"
    message_id = PrimaryKey(uuid.UUID, column="MessageId", default=uuid.uuid4)
    title = Required(str, column="Title", max_len=128)
    text = Required(str, column="Text", max_len=1024)
    recipient_type = Required(str, column="RecipientTypeId", max_len=16)
    recipient = Required(str, column="Recipient", max_len=64)
    state_id = Required(str, column="StateId", default="Created", max_len=16)
    error_message = Optional(str, column="ErrorMessage", max_len=512)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())
    # спецом храним именно id пользователя, а не всю сущность
    # для "отвязанных" адресов будет пустым
    user_id = Optional(uuid.UUID, column="UserId", nullable=True)
    notification = Required(lambda: NotificationEntity, column="NotificationId")

    def send_bus_message(self, bus_message_sender=None):
        # TODO: здесь отправляем в RabbitMQ, хотя лучше делать это НЕ здесь
        raise EntityCreationError("not implemented")

    def set_state(self, new_state_id):
        if new_state_id not in allowed_message_state_ids:
            raise EntityCreationError('{0}.ser_state() - invalid state_id - {1}'.format(
                                                        self.__class__.__name__,
                                                        new_state_id))
        self.state_id = new_state_id
        self.update_date = dt.datetime.utcnow()

if __name__ == "__main__":
    pass
    #db.bind(provider="sqlite", filename="notifications.sqlite", create_db=True)
    #db.generate_mapping(create_tables=True)
