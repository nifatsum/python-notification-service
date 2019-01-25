import smtplib, ssl
import datetime
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
import os, sys

default_login_credentials = {
    'user': 'my.dev.test.fake@gmail.com',
    'password': '51tcajKnAW1MU2O4EiTV',
    'context': ssl.create_default_context(),
    'host': 'smtp.gmail.com', 
    'port': 587
}

class EmailSender:
    def __init__(self):
        self.default_recipient='v1jprivzlrno@yandex.ru'

    def send(self, recipients, subject,
            plain_text=None, html_body=None,
            file_attachments=None, login_credentials=None):
        if not isinstance(recipients, list):
            raise ValueError('EmailSender: arg "recipients" expected as a "list(str)"')
        if not isinstance(subject, str):
            raise ValueError('EmailSender: invalid subject (str expected)')
        if len(plain_text or '') == 0 and len(html_body or '') == 0 and (
                                    not file_attachments 
                                    or len(file_attachments) == 0):
            raise ValueError('EmailSender: please specify "plain_text" or "html_body"')

        if not login_credentials:
            login_credentials = default_login_credentials

        sender_email = login_credentials['user']

        message = MIMEMultipart("alternative")
        message["Subject"] = subject #тема письма
        message["From"] = sender_email
        message["To"] = ", ".join(recipients)

        #part 1 - превью письма
        if plain_text:
            message.attach(MIMEText(plain_text, "plain"))

        #part 2 - содержимое письма
        if html_body:
            message.attach(MIMEText(html_body, "html", "utf-8"))

        #прикрепление файла
        if file_attachments and len(file_attachments) > 0:
            for fpath in file_attachments:
                part = MIMEBase('application', "octet-stream")
                part.set_payload(open(fpath, "rb").read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(fpath)))
                message.attach(part)

        context = login_credentials['context']
        host = login_credentials['host']
        port = login_credentials['port']
        password = login_credentials['password']
        with smtplib.SMTP_SSL(host=host, port=port, context=context) as server:
            server.login(user=sender_email, password=password)
            server.sendmail(from_addr=sender_email, 
                            to_addrs=recipients, 
                            msg=message.as_string())