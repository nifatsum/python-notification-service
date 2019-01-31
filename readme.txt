"система" состоит из следующих компонентов:
- notification-web-api
- RabbitMQ
- email-sender (в будущем message-sender)

запуск:
- пока не сделал docker-compose ((
- собарть\запустить контейнер для основных компонентов (docker_build.sh\docker_run.sh)

много TODO разбросано по коду.
планы по доработке:
- пеервести апи с "flask-restful" на "flask-restplus",
  т.к. в "flask-restplus" есть автогенерация swagger.
- добавить в консюмер отправку в Telegram-bot или по номеру тел.
- доработать структуру каталогов
- разбить entities.py на модуль из нескольких файлов
- сделать хоть какой-то клиент!