import yagmail

# v1jprivzlrno@yandex.ru - Y9bxRJGV5Cumehts8ykg

receiver = "v1jprivzlrno@yandex.ru"
body = "Hello there from Yagmail"
# filename = "document.pdf"

#yag = yagmail.SMTP("my@gmail.com")
yag = yagmail.SMTP('mygmailusername', 'mygmailpassword')
yag.send(
    to=receiver,
    subject="Yagmail test with attachment",
    contents=body
)