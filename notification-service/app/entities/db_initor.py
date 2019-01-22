import app.entities as e
from app.entities.user import UserEntity
from app.entities.channel import ChannelEntity
#import uuid

class DbInitor: # TODO: придумать нормальное название класса
    @staticmethod
    @e.orm.db_session
    def seed():
        def_channel = ChannelEntity.get(name='default')
        if not def_channel:
            # NOTE: может лучше юзать uuid предварительно выполнив import uuid ???
            ch_id = e.uuid.UUID('c64f941d-de0c-484d-8451-98747bbcc831') # юзаем фиксированный uuid для default канала
            def_channel = ChannelEntity(channel_id=ch_id, name='default', description='default channel')

        for i in range(1, 5):
            u_name = 'some_man_{0}'.format(i)
            u = UserEntity.get(name=u_name)
            if u:
                continue

            em = 'user{0}@email.com'.format(i)
            ph = '7922{0}'.format(str(i)*7)
            UserEntity(name=u_name, email=em, phone=ph)