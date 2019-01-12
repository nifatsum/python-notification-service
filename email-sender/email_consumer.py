import pika
import json

# https://www.rabbitmq.com/tutorials/tutorial-one-python.html


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


channel.queue_declare(queue='hello')


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    dto = json.loads(body, object_hook=as_dto_message)
    print(" [x]   ->-     {} - {} - {}".format(dto.recipient, dto.subject, dto.body))


channel.basic_consume(callback,
                      queue='hello',
                      no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
