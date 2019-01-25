import sys
import pika

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

message = ' '.join(sys.argv[1:]) or '{"recipients":"v1jprivzlrno@yandex.ru","subject":"test subject","message":"some text"}'

channel.basic_publish(exchange='', routing_key=queue_name, body=message)
print(" [x] Sent '{}'".format(message))
connection.close()
