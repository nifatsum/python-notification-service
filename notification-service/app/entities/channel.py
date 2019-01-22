from app.entities import db, orm, dt, uuid
from app.entities.address import AddressEntity
from app.entities.notification import NotificationEntity

class ChannelEntity(db.Entity):
    _table_ = "Channel"
    channel_id = orm.PrimaryKey(uuid.UUID, column="ChannelId", default=uuid.uuid4)
    name = orm.Required(str, column="Name", unique=True, max_len=64)
    description = orm.Optional(str, column="Description", nullable=True, max_len=512)
    create_date = orm.Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = orm.Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())

    addresses = orm.Set(lambda: AddressEntity)
    notifications = orm.Set(lambda: NotificationEntity)