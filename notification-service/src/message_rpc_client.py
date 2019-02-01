import pika, uuid, time, json, threading
from datetime import datetime, timedelta
import os
from src.entities import MesaageEntity, NotificationEntity, db_session, use_default_binding_settings

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
    def __init__(self, rabbit_config=None, max_retry_c=None):
        self.max_retry_count = max_retry_c if max_retry_c else max_retry_count
        self.config = rabbit_config or default_rabbit_config.copy()
        self.log_info(json.dumps(self.config, indent=4))

    # TODO: прикрутить во всем проекте нормальный логгер. например loguru
    def log_info(self, message, *args, **kwargs):
        if len(args) > 0:
            message = message.format(*args)
        elif len(kwargs) > 0:
            message = message.format(**kwargs)
        print('{0}: {1}'.format(self.__class__.__name__, message))

    def process_notification(self, notification_id, 
                        is_test=None, include_faliled=False, all_unsuccess=False):
        try:
            if not isinstance(notification_id, uuid.UUID):
                raise ValueError('MessageRpcClient - uuid is expected ofr param "notification_id"')

            self.log_info('send messages for notification "{0}". (is_test: {1}, include_faliled: {2}, all_unsuccess: {3})', 
                        notification_id, is_test, include_faliled, all_unsuccess)

            created_messages_ids = []
            with db_session:
                n = NotificationEntity[notification_id]
                tmp_list = n.messages.select(lambda m: (all_unsuccess and m.state_id in ['Error', 'Created']) or (include_faliled and m.state_id == 'Error') or m.state_id == 'Created')
                self.log_info('tmp_list count: {0}', len(tmp_list))
                tmp_id_list = [m.message_id for m in tmp_list]
                created_messages_ids.extend(tmp_id_list)

            if created_messages_ids and len(created_messages_ids) > 0:
                for m_id in created_messages_ids:
                    th = threading.Thread(target=RpcWorker(self.config, self.max_retry_count).send_message, args=[m_id, is_test])  # <- 1 element list
                    th.start()
            self.log_info('{0} msgs was sended.', len(created_messages_ids))
        except Exception as e:
            raise MessageRpcClientError('process_notification({0}) error:\n{1}'.format(notification_id, str(e)), e)

# TODO: возможно стоит переделать на класс вида "class CustomThread(threading.Thread)"
class RpcWorker:
    def __init__(self, rabbit_config, max_retry_c):
        self.max_retry_count = max_retry_c #if max_retry_c else max_retry_count
        self.config = rabbit_config #or default_rabbit_config.copy()

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

        self.exchange = None
        # self.exchange_name = None
        self.queue = None
        self.queue_name = None

        self.response_received = False

    # TODO: прикрутить во всем проекте нормальный логгер. например loguru
    def log_info(self, message, *args, **kwargs):
        if len(args) > 0:
            message = message.format(*args)
        elif len(kwargs) > 0:
            message = message.format(**kwargs)
        print('{0}: {1}'.format(self.__class__.__name__, message))

    def _open_connection(self):
        self.connection = None
        _max_retry_count = self.max_retry_count
        while not (self.connection and self.connection.is_open):
            _max_retry_count -= 1
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(**self.config))
                self.log_info('connect to Rabbit - successful')
            except pika.exceptions.AMQPError as e1:
                self.log_info('[TRY RECONNECT: max_retry_count:{0}] AMQPError: {1}', self.max_retry_count, str(e1))
                time.sleep(1)
                self.connection = None
                if self.max_retry_count <= 0:
                    raise e1

    def _check_connection_is_open(self, rabbit_connection: pika.BlockingConnection):
        if not rabbit_connection or not rabbit_connection.is_open:
            raise MessageRpcClientError('connection is closed.')

    def _check_channel_is_open(self, rabbit_channel):
        if not rabbit_channel or not rabbit_channel.is_open:
            raise MessageRpcClientError('channel is closed.')

    def _open_channel(self):
        self._check_connection_is_open(self.connection)
        self.channel = self.connection.channel()
        if self.prefetch_count:
            self.channel.basic_qos(prefetch_count=self.prefetch_count)

    def _declare_callback_queue(self):
        self._check_channel_is_open(self.channel)
        self.callback_queue = self.channel.queue_declare(**self.callback_queue_params)
        self.callback_queue_name = self.callback_queue.method.queue

    def _main_queue_bind(self):
        self._check_channel_is_open(self.channel)
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

    def _stop(self):
        if self.channel:
            self.channel.stop_consuming()
            self.channel = None

        if self.connection:
            self.connection.close()
            self.connection = None
        self.log_info('was stopped')

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
                    if m.state_id != 'Sent':
                        u_date = isoformat_to_datetime(date)
                        if error:
                            m.to_error_state(error_message=error, update_date=u_date)
                        else:
                            m.to_accepted_state(update_date=u_date)
                    is_ok = True
                else:
                    self.log_info('message "{0}" not found', message_id)
                    self.channel.basic_nack(delivery_tag=method.delivery_tag)

            if is_ok:
                if not self.no_ack:
                    self.channel.basic_ack(delivery_tag=method.delivery_tag)
                self.response_received = True
        except Exception as ex:
            if self.channel and self.channel.is_open:
                self.channel.basic_nack(delivery_tag=method.delivery_tag)
            raise CallbackProcessingError(ex)

    def send_message(self, message_id, is_test=None):
        try:
            if isinstance(message_id, str):
                message_id = uuid.UUID(message_id)
                self.log_info('send({0}) - parse "str" to uuid', message_id)

            self._open_connection()
            self._open_channel()
            self._declare_callback_queue()
            self._main_queue_bind()

            self.channel.basic_consume(consumer_callback=self.on_response, 
                                    no_ack=self.no_ack,
                                    queue=self.callback_queue_name)

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

            while not self.response_received:
                self.log_info('process_data_events...')
                self.connection.process_data_events(time_limit=None)

        except MessageRpcClientError as rpc_err:
            raise rpc_err
        except Exception as e:
            raise MessageRpcClientError('send_message({0}) error:\n{1}'.format(message_id, str(e)), e)
        finally:
            try:
                self._stop()
            except:
                pass
