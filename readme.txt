"система" состоит из следующих компонентов:
- notification-web-api
- RabbitMQ
- email-sender (в будущем message-sender)

запуск:
- собарть контейнер "web-api" (.\notification-service\docker_build.sh)
- собарть контейнер "email-sender" (.\email-sender\docker_build.sh)
- поднять docker-compose (.\docker\docker-compose.yml)


есть следующие ресурсы:
 - user (r\w)
 - address (почта\телефон) (r\w)
 - channel (канал рассылки) (r\w)
 - notifications (r)
 - messages (r)

- используется Basic авторизация
- по умолчанию создается пользователь "admin" с паролем "1234567890" и почтой "phagzkyrrw@mail.ru"
  base_auth_string: YWRtaW46TVRJek5EVTJOemc1TUE9PQ==
- по умолчанию создается default канал, при регистрации пользователя его "адреса" попадают в дефолтный канал
- уведомления можно создавать только от какого-либо канала (отправляется на все адреса канала)


данные стандартной почты:
phagzkyrrw@mail.ru
Y9bxRJGV5Cumehts8ykg


обработка уведомлений (RabbitMQ RPC):
- от указанного канала создается уведомление
- текст уведомления отправляется на все адреса прикрепленные к каналу 
  (т.е. для каждого адреса создается message в состоянии Created)

- web-api для каждой сущности message в шину отправляется событие,  
  и ожидается коллбек message.state переводим в Processing
- email-sender получает событие из шины, отправляет мыло, и бросает коллбек для апи
- web-api получает колбек пеерводит message.state в "Sent" или "Error"
  на этом цикл обработки message заканчивается



много TODO разбросано по коду.
основные планы по доработке:
- пеервести апи с "flask-restful" на "flask-restplus",
  т.к. в "flask-restplus" есть автогенерация swagger.
  в общем прикрутить swagger
- в консюмер(пока еще email-sender) добавить отправку сообщений в Telegram-bot
- доработать структуру каталогов (переименовать api\models в api\endpoints)
- разбить entities.py на модуль из нескольких файлов
- разобраться с логером (возможно заюзать стандартный модуль logging)
- отправка уведомления на определенные адреса
- сделать хоть какой-то клиент!
- healthcheck для кролика и email-sender

