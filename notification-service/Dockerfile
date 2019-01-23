FROM python:3.6.8-alpine3.8

# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y nano

COPY . /app
WORKDIR /app

EXPOSE 8000

ENTRYPOINT [ "python3", "run.py" ]
