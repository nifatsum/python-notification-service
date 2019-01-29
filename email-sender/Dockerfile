FROM python:3.6.8-alpine3.8

# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel

RUN apk update
# RUN apk add git
RUN apk add nano

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

ENTRYPOINT [ "python3", "message_rpc_server.py" ]
