import pika, uuid, time, json, threading
from datetime import datetime, timedelta
import os
#from src.entities import MesaageEntity, NotificationEntity, db_session, use_default_binding_settings

def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

    Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

    Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

    Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except:
        return False

    return str(uuid_obj) == uuid_to_test

def isoformat_to_datetime(dt_str):
    dt, _, us= dt_str.partition(".")
    dt= datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us= int(us.rstrip("Z"), 10)
    res = dt + timedelta(microseconds=us)
    return res

host = os.environ.get('RABBIT_HOST', 'localhost')
max_retry_count = os.environ.get('MAX_RETRY_COUNT', 10)
default_rabbit_config = { 
    # 'credentials': { 'username':'dev', 'password':'dev' },
    'queue': { 'queue': 'notification_message_rpc', 'durable': True },
    'exchange': { 'exchange': 'notification_rpc', 'exchange_type': 'fanout' },
    # ----------------------
    'prefetch_count': 2,
    'routing_key': 'message',
    'callback_queue': { 'queue': 'message_rpc_callback', 'durable': True, 'exclusive': False },
    # 'port': 5672,
    'host': host,
    'no_ack': False
    }

class MessageRpcClientError(Exception):
    def __init__(self, message, inner=None):
        self.message = message
        self.inner = inner
        Exception.__init__(inner)

class CallbackProcessingError(MessageRpcClientError):
    def __init__(self, inner):
        super().__init__(message=str(inner), inner=inner)

    def __str__(self):
        return 'inner({0}) - {1}'.format(type(self.inner).__name__, 
                                        str(self.inner))

class MessageRpcClient(object):
    def __init__(self, auto_start=False, rabbit_config=None, max_retry_c=None):
        self.max_retry_count = max_retry_c if max_retry_c else max_retry_count
        self.config = rabbit_config or default_rabbit_config.copy()

        self.log_info(json.dumps(self.config, indent=4))

        self.routing_key = self.config.pop('routing_key') # required
        self.callback_queue_params = self.config.pop('callback_queue') # required

        self.no_ack = self.config.pop('no_ack', True)
        self.prefetch_count = self.config.pop('prefetch_count', None)

        self.queue_params = self.config.pop('queue', {})
        self.exchange_params = self.config.pop('exchange', {})

        # convert credentials dict to pika.PlainCredentials
        _key = 'credentials'
        if _key in self.config:
            self.config[_key] = pika.PlainCredentials(**self.config[_key])

        self.connection = None
        self.channel = None
        
        self.callback_queue = None
        self.callback_queue_name = None

        self.queue = None
        self.queue_name = None
        self.exchange = None
        self.exchange_name = None

        if auto_start:
            self.start()

    # TODO: прикрутить во всем проекте нормальный логгер. например loguru
    def log_info(self, message, *args, **kwargs):
        if len(args) > 0:
            message = message.format(*args)
        elif len(kwargs) > 0:
            message = message.format(**kwargs)
        print('{0}: {1}'.format(self.__class__.__name__, message))

    def start(self):
        t = threading.Thread(target=self._start)
        t.start()
        # self._start()

    def _start(self):
        try:
            if self.channel:
                raise ValueError('MessageRpcClient - is already started')

            try:
                while not self.connection:
                    self.max_retry_count -= 1
                    try:
                        self.connection = pika.BlockingConnection(pika.ConnectionParameters(**self.config))
                    except pika.exceptions.AMQPError as e1:
                        self.log_info('[TRY RECONNECT: max_retry_count:{0}] AMQPError: {1}', self.max_retry_count, str(e1))
                        time.sleep(1)
                        if self.max_retry_count <= 0:
                            raise e1

                self.log_info('connect ot Rabbit - successful')
                self.channel = self.connection.channel()
                if self.prefetch_count:
                    self.channel.basic_qos(prefetch_count=self.prefetch_count)

                self.callback_queue = self.channel.queue_declare(**self.callback_queue_params)
                self.callback_queue_name = self.callback_queue.method.queue

                if self.queue_params:
                    self.queue = self.channel.queue_declare(**self.queue_params)
                    self.queue_name = self.queue.method.queue
                if self.exchange_params:
                    self.exchange = self.channel.exchange_declare(**self.exchange_params)
                    self.exchange_name = self.exchange_params['exchange']
                    self.exchange_type = self.exchange_params['exchange_type']

                # (опциоанльно) биндим основную очередь и обменник, если их параметры указаны
                if self.queue and self.exchange:
                    r_key = self.routing_key if self.exchange_type != 'fanout' else ''
                    self.channel.queue_bind(queue=self.queue_name, 
                                            exchange=self.exchange_name,
                                            routing_key=r_key)

                self.channel.basic_consume(consumer_callback=self.on_response, 
                                            no_ack=self.no_ack,
                                            queue=self.callback_queue_name)
            except pika.exceptions.AMQPError as ex:
                self.log_info('AMQPError: {0}', str(ex))
                self.connection = None
                raise ex

            if self.connection:
                self.log_info('start callback consuming...')
                while self.connection and self.connection.is_open:
                    try:
                        self.connection.process_data_events(time_limit=None)
                        #self.log_info('connection.process_data_events(time_limit=None) !!!!!   !!!!!!   !!!!!!')
                    except CallbackProcessingError as cpe:
                        self.log_info('CallbackProcessingError CONTINUE TO WORK !!! !!! !!!\n {0}', str(cpe))
                        #raise cpe
        except Exception as ex:
            self.log_info('_start() FATAL ERORR !!! !!! !!!  {0}', str(ex))
            self.stop()
            raise ex

    def on_response(self, ch, method, props, body):
        try:
            message_id = uuid.UUID(props.correlation_id)
            self.log_info('receive callback for "{0}". body: {1}', message_id, body)

            resp = json.loads(body)
            error = resp.get('error')
            date = resp.get('date')

            # TODO: по хорошему MessageRpcClient не должен знать о сущностях в БД
            # и сюда надо пробрасывать делегат
            is_ok = False
            with db_session:
                m = MesaageEntity.get(message_id)
                if m:
                    u_date = isoformat_to_datetime(date)
                    if error:
                        m.to_error_state(error_message=error, update_date=u_date)
                    else:
                        m.to_accepted_state(update_date=u_date)
                    is_ok = True
                else:
                    self.log_info('message "{0}" not found', message_id)

            if is_ok and not self.no_ack:
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as ex:
            raise CallbackProcessingError(ex)

    def stop(self):
        if self.channel:
            self.channel.stop_consuming()
            self.channel = None

        if self.connection:
            self.connection.close()
            self.connection = None
        self.log_info('was stopped')

    def process_notification(self, notification_id, 
                        is_test=None, 
                        include_faliled=False, 
                        all_unsuccess=False):
        try:
            if not self.channel:
                raise ValueError('MessageRpcClient - is not started')

            if not isinstance(notification_id, uuid.UUID):
                raise ValueError('MessageRpcClient - uuid is expected ofr param "notification_id"')

            self.log_info('send messages for notification "{0}". (is_test: {1}, include_faliled: {2}, all_unsuccess: {3})', 
                        notification_id, is_test, include_faliled, all_unsuccess)

            created_messages_ids = []
            with db_session:
                n = NotificationEntity[notification_id]
                tmp_list = n.messages.select(lambda m: (all_unsuccess and m.state_id in ['Error', 'Created']) or (include_faliled and m.state_id == 'Error') or m.state_id == 'Created')
                self.log_info('tmp_list count: {0}', len(tmp_list))
                created_messages_ids.extend([m.message_id for m in tmp_list])

            if created_messages_ids and len(created_messages_ids) > 0:
                for m_id in created_messages_ids:
                    self.send_message(message_id=m_id, is_test=is_test)
            self.log_info('{0} msgs was sended.', len(created_messages_ids))
        except Exception as e:
            raise MessageRpcClientError(str(e), e)

    def send_message(self, message_id, is_test=None):
        try:
            if not self.channel:
                raise ValueError('MessageRpcClient - is not started')

            if isinstance(message_id, str):
                message_id = uuid.UUID(message_id)
                self.log_info('send({0}) - parse "str" to uuid', message_id)

            msg_dict = {}
            with db_session:
                m = MesaageEntity[message_id]
                if m.state_id == 'Sent':
                    raise ValueError('message [{0}] - is already processed'.format(message_id))
                elif m.state_id == 'Processing':
                    raise ValueError('message [{0}] - was is already sended to message broker'.format(message_id))
                elif m.state_id in ['Error', 'Created']:
                    m.to_processing()

                msg_dict['recipient_type'] = m.recipient_type
                msg_dict['recipients'] = m.recipient
                msg_dict['subject'] = m.title
                msg_dict['message'] = m.text
                if is_test:
                    msg_dict['is_test'] = True
            body_str = json.dumps(msg_dict)
            self.channel.basic_publish(exchange=self.exchange_name,
                                    routing_key=self.routing_key,
                                    properties=pika.BasicProperties(
                                            reply_to=self.callback_queue_name,
                                            correlation_id=str(message_id)
                                            ),
                                    body=body_str)
            self.log_info('publish message [{0}]. sended data: {1}', message_id, body_str)
        except Exception as e:
            raise MessageRpcClientError(str(e), e)


if __name__ != '__main__':
    from src.entities import MesaageEntity, NotificationEntity, db_session, use_default_binding_settings
else:
    from entities import MesaageEntity, NotificationEntity, db_session, use_default_binding_settings
    import sys
    use_default_binding_settings()
    c = MessageRpcClient()
    c.start()
    time.sleep(0.1)

    stop_words = ['q', 'exit', 'c', 'quit', 'cancel', 'abort']
    print('statrt check user input...')
    print('stop_words: {0}'.format(stop_words))

    def dispose_and_exit(exit_code=0):
        c.stop()
        sys.exit(exit_code)

    proc_notif_param = "-n "
    while True:
        try:
            print('enter message_id:')
            user_input = input()
            # print('user_input: ', user_input)
            if user_input in ['--help', 'help', '-h']:
                print('stop_words: {0}'.format(stop_words))
            elif user_input in stop_words:
                print('stop word catched !')
                dispose_and_exit(1)
            elif user_input.startswith(proc_notif_param):
                user_input = user_input.replace(proc_notif_param, '').strip()

                all_unsuccess = False
                all_unsuccess_param = '--all'
                if all_unsuccess_param in user_input:
                    user_input = user_input.replace(all_unsuccess_param, '').strip()
                    all_unsuccess = True

                include_faliled = False
                include_faliled_param = '--failed'
                if include_faliled_param in user_input:
                    user_input = user_input.replace(include_faliled_param, '').strip()
                    include_faliled = True

                notification_id = uuid.UUID(user_input)
                c.process_notification(notification_id=notification_id,
                                    is_test=True, 
                                    include_faliled=include_faliled,
                                    all_unsuccess=all_unsuccess)
            else:
                c.send_message(message_id=user_input, is_test=True)
        except Exception as ex:
            print('@@ Exception {0}: {1}'.format(type(ex).__name__, ex))
        except KeyboardInterrupt:
            print('@@ KeyboardInterrupt')
            dispose_and_exit(0)