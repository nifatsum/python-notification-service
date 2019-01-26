import pika
import json
from email_sender import EmailSender


class DTOMessage(object):
    def __init__(self, recipient_type, recipients, subject, message):
        self.recipient_type = recipient_type
        self.recipients = recipients if isinstance(recipients, list) else recipients.replace(',', ';').repclace(' ', '').split(';')
        if len(self.recipients) == 0:
            raise ValueError('Please specify "recipients"')
        self.subject = subject
        self.body = message

    @staticmethod
    def from_dict(dct):
        return DTOMessage(dct['recipient_type'], dct['recipients'], dct["subject"], dct['message'])


default_rabbit_config = { 
    'host': 'localhost', 
    # 'port': 5672,
    # 'username':'dev', 'password':'dev',
    'queue': 'notification_message_rpc'
    }

class MessageConsumerRPC:
    def __init__(self, rabbit_config=None):
        self.config = rabbit_config or default_rabbit_config.copy()
        
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

    def start(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(**self.config))
        self.channel = self.connection.channel()        
        self.queue = self.channel.queue_declare(queue=self.queue_name, durable=self.durable)
        self.channel.basic_qos(prefetch_count=1)

        def on_request(ch, method, props, body):
            dto = json.loads(body, object_hook=DTOMessage.from_dict)
            resp = { 'success': True }
            try:
                if dto.recipient_type == 'email':
                    self.email_sender.send(recipients=dto.recipients, 
                                        subject=dto.subject, 
                                        plain_text=dto.body)
                    
                else:
                    raise ValueError('Unsupported recipient_type.')
            except Exception as ex:
                resp['success'] = False
                resp['error'] = ex

            ch.basic_publish(exchange='',
                            routing_key=props.reply_to,
                            properties=pika.BasicProperties(correlation_id=props.correlation_id),
                            body=str(resp))
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        self.channel.basic_consume(on_request, queue=self.queue_name)
        print("- Awaiting RPC requests")
        self.channel.start_consuming()
    def stop(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()
