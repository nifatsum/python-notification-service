import pika
import json
from email_sender import EmailSender


class DTOMessage(object):
    def __init__(self, recipient, subject, message):
        self.subject = subject
        self.recipient = recipient
        self.body = message


def as_dto_message(dct):
    return DTOMessage(dct['recipient'], dct["subject"], dct['message'])


credentials = pika.PlainCredentials('dev', 'dev')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='task_queue', durable=True)

email_sender = EmailSender()


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    dto = json.loads(body, object_hook=as_dto_message)
    print(" [x]   ->-     {} - {} - {}".format(dto.recipient, dto.subject, dto.body))
    email_sender.send(dto.recipient, dto.subject, dto.body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback, queue='task_queue')

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
