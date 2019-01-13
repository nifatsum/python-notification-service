import sys
import pika

credentials = pika.PlainCredentials('dev', 'dev')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='task_queue', durable=True)
message = ' '.join(sys.argv[1:]) or '{"recipient":"v1jprivzlrno@yandex.ru","subject":"test subject","message":"some text"}'
channel.basic_publish(exchange='',
                      routing_key='task_queue',
                      body=message)
print(" [x] Sent '{}'".format(message))
connection.close()
