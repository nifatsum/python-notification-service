import pika
import json
from email_sender import EmailSender


class DTOMessage(object):
    def __init__(self, recipients, subject, message):
        self.subject = subject
        self.recipients = recipients
        self.body = message
    @staticmethod
    def from_dict(dct):
        return DTOMessage(dct['recipients'], dct["subject"], dct['message'])


rabbit_config = { 
    'host': 'localhost', 
    #'username':'dev', 'password':'dev',
    'queue': 'task_queue'
    }

connection_credentials = {}
if 'username' in rabbit_config:
    connection_credentials['username'] = rabbit_config['username']
if 'password' in rabbit_config:
    connection_credentials['password'] = rabbit_config['password']

credentials = (pika.PlainCredentials(**connection_credentials)
                if isinstance(connection_credentials, dict) and connection_credentials
                else pika.ConnectionParameters._DEFAULT())

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbit_config['localhost'], 
                                                            credentials=credentials))
channel = connection.channel()
queue_name = rabbit_config['queue']
channel.queue_declare(queue=queue_name, durable=True)

email_sender = EmailSender()

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    dto = json.loads(body, object_hook=DTOMessage.from_dict)
    print(" [x]   ->-     {} - {} - {}".format(dto.recipient, dto.subject, dto.body))
    rec_list = []
    for i in dto.recipients.split(';'):
        for r in i.split(','):
            rec_list.append(r.strip())
    email_sender.send(recipients=rec_list, subject=dto.subject, plain_text=dto.body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback, queue='task_queue')

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
