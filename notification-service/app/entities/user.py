from app.entities import db, orm, dt, uuid, EntityCreationError
from app.entities.address import AddressEntity, allowed_address_types
from app.entities.channel import ChannelEntity

class UserEntity(db.Entity):
    _table_ = "User"
    # TODO: set user_id as bigint
    user_id = orm.PrimaryKey(uuid.UUID, column="UserId", default=uuid.uuid4) 
    password_hash = orm.Optional(str, column="PasswordHash", nullable=True, max_len=64)
    name = orm.Required(str, column="Name", unique=True, max_len=64)
    email = orm.Optional(str, column="Email", nullable=True, max_len=64)
    phone = orm.Optional(str, column="Phone", nullable=True, max_len=32)
    create_date = orm.Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = orm.Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())

    addresses = orm.Set(lambda: AddressEntity)

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
        raise orm.OrmError("not implemented")

    def update_phone(self, new_phone):
        # TODO: *
        raise orm.OrmError("not implemented")