import pika, json, time, threading
from datetime import datetime
from email_sender import EmailSender
from logger import LoggerProxy
import os

# TODO: заменить на "namedtuple"
class DTOMessage(object):
    def __init__(self, recipient_type, recipients, subject, message, is_test=None):
        self.recipient_type = recipient_type
        self.recipients = recipients if isinstance(recipients, list) else recipients.replace(',', ';').replace(' ', '').split(';')
        if len(self.recipients) == 0:
            raise ValueError('Please specify "recipients"')
        self.subject = subject
        self.body = message
        self.is_test = is_test if isinstance(is_test, bool) else False

    @staticmethod
    def from_dict(dct):
        # print('dct:', dct)
        return DTOMessage(
                    dct['recipient_type'], 
                    dct['recipients'], 
                    dct["subject"], 
                    dct['message'],
                    is_test=dct.get('is_test', False))

host = os.environ.get('RABBIT_HOST', 'localhost')
max_retry_count = int(os.environ.get('MAX_RETRY_COUNT', '10'))
default_reconnect_delay = int(os.environ.get('RABBIT_RECONNECT_DELAY', '5'))

default_rabbit_config = { 
    'host': host, 
    # 'port': 5672,
    # 'username':'dev', 'password':'dev',
    'queue': 'notification_message_rpc',
    'durable': True
    }

class MessageConsumerRPC:
    # TODO: переработать методы аналогично message_rpc_client
    def __init__(self, rabbit_config=None, max_retry_c=None, reconnect_delay=None):
        self.max_retry_count = max_retry_c if max_retry_c else max_retry_count
        self.config = rabbit_config or default_rabbit_config.copy()
        self.reconnect_delay = reconnect_delay or default_reconnect_delay
        
        self.durable = self.config.pop('durable', False)
        self.queue_name = self.config.pop('queue', None)
        if not self.queue_name:
            raise ValueError('key "queue" is not specified in rabbit_config.')      

        connection_credentials = {}
        for k in ['username', 'password']:
            if k in self.config:
                connection_credentials[k] = self.config.pop(k)

        if isinstance(connection_credentials, dict) and connection_credentials:
            self.config['credentials'] = pika.PlainCredentials(**connection_credentials)
        self.connection = None
        self.channel = None
        self.queue = None
        self.email_sender = EmailSender()
        self.__logger = LoggerProxy('{0}_{1}'.format(self.__class__.__name__, 
                                                    datetime.strftime(datetime.utcnow(), '%Y%m%dT%H00')))

    def log_info(self, message, *args, **kwargs):
        self.__logger.info(message, *args, **kwargs)

    def start(self):
        t = threading.Thread(target=self._start)
        t.start()

    def _start(self):
        while not self.connection:
            self.max_retry_count -= 1
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(**self.config))
                self.log_info('connect to Rabbit - successful')
            except pika.exceptions.AMQPError as e1:
                self.log_info('[TRY RECONNECT: max_retry_count:{0}] AMQPError: {1}', self.max_retry_count, str(e1))
                time.sleep(self.reconnect_delay)
                if self.max_retry_count <= 0:
                    raise e1

        self.channel = self.connection.channel()
        self.queue = self.channel.queue_declare(queue=self.queue_name, durable=self.durable)
        self.channel.basic_qos(prefetch_count=1)

        def on_request(ch, method, props, body):
            self.log_info('"{0}" - on_request body: {1}', props.correlation_id, body)
            dto = json.loads(body, object_hook=DTOMessage.from_dict)
            resp = { 'success': True }
            try:
                if dto.recipient_type == 'email':
                    if dto.is_test:
                        self.log_info('"{0}" - dto.is_test: {1}', props.correlation_id, dto.is_test)
                    else:
                        self.email_sender.send(recipients=dto.recipients, 
                                            subject=dto.subject, 
                                            plain_text=dto.body)
                else:
                    raise ValueError('Unsupported recipient_type: {0}.'.format(dto.recipient_type))
            except Exception as ex:
                resp['success'] = False
                resp['error'] = str(ex)
            resp['date'] = datetime.utcnow().isoformat()
            callback_body = json.dumps(resp)
            ch.basic_publish(exchange='',
                            routing_key=props.reply_to,
                            properties=pika.BasicProperties(correlation_id=props.correlation_id),
                            body=callback_body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.log_info('{0} - sended callback: {1}', props.correlation_id, callback_body)
        
        self.channel.basic_consume(on_request, queue=self.queue_name)

        self.log_info("Awaiting RPC requests")
        #self.channel.start_consuming()
        while self.connection and self.connection.is_open:
            self.connection.process_data_events(time_limit=None)

    def stop(self):
        try:
            self.channel.stop_consuming()
        except Exception as ex:
            self.log_info('channel.stop_consuming() error: {0}', str(ex))

        try:
            self.channel.close()            
        except Exception as ex:
            self.log_info('channel.close() error: {0}', str(ex))
        self.channel = None

        try:
            self.connection.close()            
        except Exception as ex:
            self.log_info('connection.close() error: {0}', str(ex))
        self.connection = None
        self.log_info("was stopped")


if __name__ == '__main__':
    import sys
    c = MessageConsumerRPC()
    c._start()

    # stop_words = ['q', 'exit', 'c', 'quit', 'cancel', 'abort']
    # print('statrt check user input...')
    # print('stop_words: {0}'.format(stop_words))

    # def dispose_and_exit(exit_code=0):
    #     c.stop()
    #     sys.exit(exit_code)

    # while True:
    #     try:
    #         print('enter command:')
    #         user_input = input()

    #         if user_input in ['--help', 'help', '-h']:
    #             print('stop_words: {0}'.format(stop_words))
    #         elif user_input in stop_words:
    #             print('stop word catched !')
    #             dispose_and_exit(1)
    #         else:
    #             print('user_input:', user_input)
    #     except ValueError as ex:
    #         print('Exception {0}: {1}'.format(type(ex).__name__, ex))
    #     except KeyboardInterrupt:
    #         print('KeyboardInterrupt')
    #         dispose_and_exit(0)