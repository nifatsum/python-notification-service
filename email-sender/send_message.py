import pika

credentials = pika.PlainCredentials('dev', 'dev')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))
channel = connection.channel()


channel.queue_declare(queue='emails')

channel.basic_publish(exchange='',
                      routing_key='hello',
                      body='{"recipient":"my@mail.ru","subject":"test subject","message":"some text"}')
print(" [x] Sent 'Hello World!'")
connection.close()
