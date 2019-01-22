from app.entities import db, orm, dt, uuid, EntityCreationError
from app.entities.notification import NotificationEntity

allowed_message_states = ["Created", "Processing", "Sent", "Error"]
class MesaageEntity(db.Entity):
    _table_ = "NotificationMesaage"
    message_id = orm.PrimaryKey(uuid.UUID, column="MessageId", default=uuid.uuid4)
    title = orm.Required(str, column="Title", max_len=128)
    text = orm.Required(str, column="Text", max_len=1024)
    recipient_type = orm.Required(str, column="RecipientTypeId", max_len=16)
    recipient = orm.Required(str, column="Recipient", max_len=64)
    state_id = orm.Required(str, column="StateId", default="Created", max_len=16)
    error_message = orm.Optional(str, column="ErrorMessage", max_len=512)
    create_date = orm.Required(dt.datetime, column="CreateDate", default=dt.datetime.utcnow())
    update_date = orm.Required(dt.datetime, column="UpdateDate", default=dt.datetime.utcnow())

    # спецом храним именно id пользователя и канала, а не всю сущность
    # для "отвязанных" адресов будет пустым
    user_id = orm.Optional(uuid.UUID, column="UserId", nullable=True)
    channel_id = orm.Optional(uuid.UUID, column="ChannelId", nullable=True)

    notification = orm.Required(lambda: NotificationEntity, column="NotificationId")

    def send_bus_message(self, bus_message_sender=None):
        # TODO: здесь отправляем в RabbitMQ, хотя лучше делать это НЕ здесь
        raise EntityCreationError("not implemented")

    def set_state(self, new_state_id):
        if new_state_id not in allowed_message_states:
            raise EntityCreationError('{0}.ser_state() - invalid state_id - {1}'.format(
                                                        self.__class__.__name__,
                                                        new_state_id))
        self.state_id = new_state_id
        self.update_date = dt.datetime.utcnow()