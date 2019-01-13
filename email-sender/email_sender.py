import yagmail


class EmailSender(object):
    def __init__(self, login=None, password=None):
        self.default_login='my.dev.test.fake@gmail.com'
        self.default_recipient='v1jprivzlrno@yandex.ru'
        self.login = self.default_login if login is None else login
        self.password = '51tcajKnAW1MU2O4EiTV' if password is None else password
        self.yag_client = yagmail.SMTP(self.login, self.password)

    def send(self, recipient, subject, body):
        self.yag_client.send(to=recipient, subject=subject, contents=body)
        print(' [EmailSender]: Send email to "{}" with subject "{}"'.format(recipient, subject))


# v1jprivzlrno@yandex.ru - Y9bxRJGV5Cumehts8ykg
#receiver = "v1jprivzlrno@yandex.ru"
#body = "Hello there from Yagmail"
#subject="Yagmail test with attachment (maybe)",
# filename = "document.pdf"

#sender = EmailSender()
#sender.send(sender.default_recipient, 'instance send method2', 'some body text')
