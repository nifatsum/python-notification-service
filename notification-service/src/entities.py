from decimal import Decimal
import datetime as dt
import uuid
import json
from pony.orm import (db_session, Database, PrimaryKey, 
                        Required, Optional, OrmError, 
                        Set, ObjectNotFound, composite_key)
# from passlib.apps import custom_app_context as pwd_context
from passlib.context import CryptContext # as pwd_context
db = Database()
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "des_crypt"])

def use_default_binding_settings():
    db.bind(provider="sqlite", filename="./../assets/notifications.sqlite", create_db=True)
    db.generate_mapping(create_tables=True)
    DbInitor.seed()
    print('default_binding_settings - is used')

class DbInitor: # TODO: придумать нормальное название класса
    @staticmethod
    @db_session
    def seed():
        def_channel = ChannelEntity.get(name='default')
        if not def_channel:
            # юзаем фиксированный uuid для default канала
            ch_id = uuid.UUID('c64f941d-de0c-484d-8451-98747bbcc831')
            def_channel = ChannelEntity(channel_id=ch_id, 
                                        name='default', 
                                        description='default channel')

        u_name = 'admin'
        admin = UserEntity.get(name=u_name)
        if not admin:
            admin_pass_hash = 'MTIzNDU2Nzg5MA==' # equal 1234567890
            admin = UserEntity(name=u_name, 
                            email='phagzkyrrw@mail.ru', 
                            password_hash=admin_pass_hash)
            # base_auth_string: YWRtaW46TVRJek5EVTJOemc1TUE9PQ==

        test_email_list = ['v1jprivzlrno@yandex.ru', 'v1jprivzlrno@mail.ru']
        if not UserEntity.exists():
            for i in range(0, len(test_email_list)):
                u_name = 'some_man_{0}'.format(i+1)
                u = UserEntity.get(name=u_name)
                if u:
                    continue
                e = test_email_list[i]
                p = None # '7922{0}'.format(str(i)*7)
                pass_hash = 'MTIzNDU2Nzg=' # equal = '12345678'
                UserEntity(name=u_name, email=e, phone=p, password_hash=pass_hash)

class EntityCreationError(OrmError):
    def __init__(self, message, inner=None, *args, **kwargs):
        self.message = message
        self.inner = inner
        super().__init__(message)

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
    password_hash = Required(str, column="PasswordHash", max_len=255)
    name = Required(str, column="Name", unique=True, max_len=64)
    email = Optional(str, column="Email", nullable=True, max_len=64)
    phone = Optional(str, column="Phone", nullable=True, max_len=32)
    create_date = Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())
    addresses = Set(lambda: AddressEntity)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def before_insert(self):
        if len(self.email or '') == 0 and len(self.phone or '') == 0:
            m = '({0})you must specify an "email" or "phone"'
            raise EntityCreationError(m.format(self.__class__.__name__))
        pass_hash = pwd_context.hash(secret='{0}{1}'.format(self.password_hash, self.user_id))
        self.password_hash = pass_hash

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
        # TODO: обновить сущность Address
        raise EntityCreationError("not implemented")

    def update_phone(self, new_phone):
        # TODO: обновить сущность Address
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

    composite_key(type_id, recipient)

    def before_insert(self):
        if self.type_id not in allowed_address_types:
            m = "({0}) allowed types is {1}"
            raise EntityCreationError(m.format(self.__class__.__name__, 
                                allowed_address_types))

    def update_recipient(self, new_recipient):
        raise OrmError('update_recipient - is not implemented')
        # TODO: add validation
        # self.recipient = new_recipient
        # # TODO: update user credentionals if need
        # self.update_date = dt.datetime.utcnow()

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
        if len(self.addresses) == 0 and self.channel.addresses.count() > 0:
            for a in self.channel.addresses.select():
                self.addresses.add(a)
        if len(self.addresses) == 0:
            raise EntityCreationError("NotificationEntity - address list is empty")

    def after_insert(self):
        for a in self.addresses.select():
            self.messages.create(title=self.title,
                                text=self.text,
                                recipient_type=a.type_id,
                                recipient=a.recipient,
                                address_id=a.address_id,
                                user_id=a.user.user_id if a.user else None)

#-------------------------------------------------------------

allowed_message_state_ids = ["Created", "Processing", "Sent", "Error"]
allowed_message_state_maps = {
    "Created": ["Processing"],
    "Processing": ["Sent", "Error"],
    "Error": ["Processing"]
}
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
    # спецом храним именно id пользователя и адреса, а не всю сущность
    # для "отвязанных" адресов будет пустым
    address_id = Optional(uuid.UUID, column="AddressId", nullable=True)
    user_id = Optional(uuid.UUID, column="UserId", nullable=True)
    notification = Required(lambda: NotificationEntity, column="NotificationId")

    def send_bus_message(self, bus_message_sender=None):
        # TODO: здесь отправляем в RabbitMQ, хотя лучше делать это НЕ здесь
        raise EntityCreationError("not implemented")

    def to_accepted_state(self, update_date=None):
        self.__set_state('Sent', update_date=update_date)

    def to_error_state(self, error_message, update_date=None):
        self.__set_state('Error', error_message=error_message, update_date=update_date)

    def to_processing(self, update_date=None):
        self.__set_state('Processing', update_date=update_date)

    def __set_state(self, new_state_id, update_date=None, error_message=None):
        prefix = '{0}[{1}].set_state()'.format(self.__class__.__name__, self.message_id)
        if new_state_id not in allowed_message_state_ids:
            raise OrmError('{0} - invalid state_id "{1}"'.format(prefix, new_state_id))
        s_map = allowed_message_state_maps.get(self.state_id)
        if not s_map or new_state_id not in s_map:
            raise OrmError('{0} - can`t change state. ("{1}" -> "{2}")'.format(prefix, 
                                                                                self.state_id, 
                                                                                new_state_id))
        if new_state_id == 'Error' and not error_message:
            raise OrmError('{0} - "error_message" param is not specified.'.format(prefix))

        #print('set_state({0}): "{1}" --> "{2}"'.format(self.message_id, self.state_id, new_state_id))
        if error_message:
            self.error_message = error_message
        self.state_id = new_state_id
        self.update_date = update_date or dt.datetime.utcnow()

if __name__ == "__main__":
    pass
    #db.bind(provider="sqlite", filename="notifications.sqlite", create_db=True)
    #db.generate_mapping(create_tables=True)
