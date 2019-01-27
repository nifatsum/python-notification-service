import pika, uuid, time, json, threading
from datetime import datetime, timedelta
from entities import MesaageEntity, db_session, use_default_binding_settings

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

default_rabbit_config = { 
    # 'credentials': { 'username':'dev', 'password':'dev' },
    'queue': { 'queue': 'notification_message_rpc', 'durable': True },
    'exchange': { 'exchange': 'notification_rpc', 'exchange_type': 'fanout' },
    # ----------------------
    'prefetch_count': 2,
    'routing_key': 'message',
    'callback_queue': { 'queue': 'message_rpc_callback', 'durable': True, 'exclusive': False },
    # 'port': 5672,
    'host': 'localhost',
    'no_ack': False
    }

class CallbackProcessingError(Exception):
    def __init__(self, inner):
        self.inner = inner
    def __str__(self):
        return 'inner({0}) - {1}'.format(type(self.inner).__name__, 
                                        str(self.inner))

class MessageRpcClient(object):
    def __init__(self, auto_start=False, rabbit_config=None):
        self.config = rabbit_config or default_rabbit_config.copy()

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
        self.__is_started = False

        if auto_start:
            self.start()

    def start(self):
        t = threading.Thread(target=self._start)
        t.start()
        # self._start()

    def _start(self):
        try:
            if self.__is_started:
                raise ValueError('MessageRpcClient - is already started')

            self.connection = pika.BlockingConnection(pika.ConnectionParameters(**self.config))

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

            print('MessageRpcClient - start callback consuming...')
            self.__is_started = True
            while self.__is_started and self.connection:
                self.connection.process_data_events(time_limit=None)
                print('connection.process_data_events(time_limit=None) !!!!!   !!!!!!   !!!!!!')
        except CallbackProcessingError as cpe:
            raise cpe
        except Exception as ex:
            print('###', ex)
            self._stop()
            raise ex

    def on_response(self, ch, method, props, body):
        try:
            message_id = uuid.UUID(props.correlation_id)
            print('receive callback for "{0}". body: {1}'.format(message_id, body))

            def isoformat_to_datetime(dt_str):
                dt, _, us= dt_str.partition(".")
                dt= datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
                us= int(us.rstrip("Z"), 10)
                res = dt + timedelta(microseconds=us)
                return res

            resp = json.loads(body)
            error = resp.get('error')
            date = resp.get('date')
            
            with db_session:
                m = MesaageEntity[message_id]
                u_date = isoformat_to_datetime(date)
                if error:
                    m.to_error_state(error_message=error, update_date=u_date)
                else:
                    m.to_accepted_state(update_date=u_date)
            
            if not self.no_ack:
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as ex:
            raise CallbackProcessingError(ex)

    def _stop(self):
        if self.channel:
            # print('dispose channel')
            self.channel.stop_consuming()
            self.channel = None
            # print('dispose channel - success')

        if self.connection:
            # print('dispose connection')
            self.connection.close()
            self.connection = None
            # print('dispose connection - success')

        self.__is_started = False
        print('MessageRpcClient - stopped')

    def stop(self):
        if self.__is_started:
            self._stop()

    def send(self, message_id, is_test=None):
        if not self.__is_started or not self.channel:
            raise ValueError('MessageRpcClient - is not started')

        if isinstance(message_id, str):
            message_id = uuid.UUID(message_id)
            print('{0}.send({1})  - parse "str" to uuid'.format(self.__class__.__name__, message_id))

        msg_dict = {}
        with db_session:
            m = MesaageEntity[message_id]
            if m.state_id == 'Sent':
                raise ValueError('message [{0}] - is already processed'.format(message_id))

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
        print('publish message [{0}]. sended data: {1}'.format(message_id, body_str))


if __name__ == '__main__':
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
            else:
                c.send(message_id=user_input, is_test=True)
        except Exception as ex:
            print('Exception {0}: {1}'.format(type(ex).__name__, ex))
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            dispose_and_exit(0)