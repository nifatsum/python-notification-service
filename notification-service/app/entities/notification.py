from app.entities import db, orm, dt, uuid
from app.entities.address import AddressEntity
from app.entities.channel import ChannelEntity
from app.entities.message import MesaageEntity, allowed_message_states

class NotificationEntity(db.Entity):
    """
    всегда создается от имени какого-либо канала (по умолчанию от default)\n
    можно непосредственно указать список адресов, иначе берутся адреса канала
    """
    _table_ = "Notification"
    notification_id = orm.PrimaryKey(uuid.UUID, column="NotificationId", default=uuid.uuid4)
    external_id = orm.Required(str, column="ExternalId", unique=True, max_len=64)
    title = orm.Required(str, column="Title", max_len=128)
    text = orm.Required(str, column="Text", max_len=1024)
    create_date = orm.Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())

    addresses = orm.Set(lambda: AddressEntity)
    channel = orm.Required(lambda: ChannelEntity, column="ChannelId")
    messages = orm.Set(lambda: MesaageEntity)

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
