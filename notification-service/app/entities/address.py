from app.entities import db, orm, dt, uuid, EntityCreationError
from app.entities.user import UserEntity
from app.entities.channel import ChannelEntity
from app.entities.notification import NotificationEntity

allowed_address_types = ["email", "phone"]
class AddressEntity(db.Entity):
    _table_ = "Address"
    address_id = orm.PrimaryKey(uuid.UUID, column="AddressId", default=uuid.uuid4)
    type_id = orm.Required(str, column="TypeId", max_len=16)
    recipient = orm.Required(str, column="Recipient", max_len=64)
    create_date = orm.Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = orm.Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())

    user = orm.Optional(lambda: UserEntity, column="UserId")
    channels = orm.Set(lambda: ChannelEntity)
    notifications = orm.Set(lambda: NotificationEntity)

    def before_insert(self):
        if self.type_id not in allowed_address_types:
            m = "({0}) allowed types is {1}"
            raise EntityCreationError(m.format(self.__class__.__name__, 
                                allowed_address_types))

    def update_recipient(self, new_recipient):
        raise orm.OrmError('update_recipient - is not implemented')
        # TODO: add validation
        # self.recipient = new_recipient
        # # TODO: update user credentionals if need
        # self.update_date = datetime.utcnow()