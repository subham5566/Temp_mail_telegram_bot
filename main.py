import requests
import random
import string
import os
from dotenv.main import load_dotenv
import telebot
import asyncio
from telebot.async_telebot import AsyncTeleBot
import sqlite3
import datetime
from threading import Thread
import schedule
from time import sleep

load_dotenv()
token = os.environ['TOKEN']

API = 'https://www.1secmail.com/api/v1/'
domain_list = [
    "1secmail.com",
    "1secmail.org",
    "1secmail.net",
    "wwjmp.com",
    "esiix.com",
    "xojxe.com",
    "yoggm.com"
]
domain = random.choice(domain_list)


connect = sqlite3.connect('base.db')  # Database creation
cursor = connect.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS used_mails(
   id INTEGER NOT NULL PRIMARY KEY,
   name INT NOT NULL,
   mail TEXT,
   date DATETIME
   );
""")

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
   id INT NOT NULL PRIMARY KEY,
   date DATETIME
   );
""")


bot = AsyncTeleBot(token)


def delete_old_records():
    # Подключение к базе данных
    connect = sqlite3.connect('base.db')  # Database creation
    cursor = connect.cursor()

    # Вычисление времени удаления
    delete_time = datetime.datetime.now() - datetime.timedelta(hours=2)

    # Выполнение запроса DELETE
    cursor.execute("DELETE FROM used_mails WHERE date < ?", (delete_time,))
    connect.commit()
    connect.close()


def generate_username():
    name = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(name) for i in range(10))

    return username


def delete_mail_t(mail=''):
    url = 'https://www.1secmail.com/mailbox'

    data = {
        'action': 'deleteMailbox',
        'login': mail.split('@')[0],
        'domain': mail.split('@')[1]
    }

    _ = requests.post(url, data=data)

    cursor.execute("DELETE FROM used_mails WHERE mail = ?", (mail,))
    connect.commit()


async def check_mail_t(message, mail=''):
    req_link = f'{API}?action=getMessages&login=\
{mail.split("@")[0]}&domain={mail.split("@")[1]}'
    r = requests.get(req_link).json()
    length = len(r)

    if length == 0:
        await bot.send_message(message.chat.id, '[INFO] На почте пока \
нет новых сообщений.')
    else:
        id_list = []

        for i in r:
            for k, v in i.items():
                if k == 'id':
                    id_list.append(v)

        await bot.send_message(message.chat.id,
                               f'[+] У вас {length} входящих!')

        for i in id_list:
            read_msg = f'{API}?action=readMessage&login=\
{mail.split("@")[0]}&domain={mail.split("@")[1]}&id={i}'
            r = requests.get(read_msg).json()

            sender = r.get('from')
            subject = r.get('subject')
            date = r.get('date')
            content = r.get('textBody')

            await bot.send_message(message.chat.id, f'Sender: {sender}\nTo: \
{mail}\nSubject: {subject}\nDate: {date}\nContent: {content}')


@bot.message_handler(commands=["start"])
async def start(message, res=False):
    await bot.send_message(message.chat.id, 'Hello')
    try:
        cursor.execute("INSERT INTO users VALUES(?, ?)",
                       (message.chat.id, datetime.datetime.now()))
        connect.commit()
    except Exception:
        pass


@bot.message_handler(commands=["my_mails"])
async def my_mails(message):
    cursor.execute(
        f'SELECT mail FROM used_mails WHERE name={message.chat.id};')
    results = cursor.fetchall()
    mails = [row[0] for row in results]
    if mails != []:
        text = 'Ваши адреса:\n'
        text += '\n'.join(mails)
    else:
        text = 'У вас нет доступных адресов'
    await bot.send_message(message.chat.id, f'{text}')


@bot.message_handler(commands=["create_mail"])
async def create_mail(message):
    username = generate_username()
    mail = f'{username}@{domain}'
    _ = requests.get(f'{API}?login=\
{mail.split("@")[0]}&domain={mail.split("@")[1]}')
    await bot.send_message(message.chat.id, f'[+] Ваш почтовый адрес: {mail}')
    cursor.execute("INSERT INTO used_mails(name, mail, date) VALUES(?, ?, ?)",
                   (message.chat.id, mail, datetime.datetime.now()))
    connect.commit()


@bot.message_handler(commands=["check_mail"])
async def check_mail(message):
    cursor.execute(
        f'SELECT mail FROM used_mails WHERE name={message.chat.id};')
    results = cursor.fetchall()
    mails = [row[0] for row in results]

    markup = telebot.types.InlineKeyboardMarkup()
    for i in mails:
        markup.add(telebot.types.InlineKeyboardButton(
                   f"{i}", callback_data=f'0|{i}'))

    await bot.send_message(message.chat.id,
                           "Какой адрес проверить:", reply_markup=markup)


@bot.message_handler(commands=["delete_mail"])
async def delete_mail(message):
    cursor.execute(
        f'SELECT mail FROM used_mails WHERE name={message.chat.id};')
    results = cursor.fetchall()
    mails = [row[0] for row in results]

    markup = telebot.types.InlineKeyboardMarkup()
    for i in mails:
        markup.add(telebot.types.InlineKeyboardButton(
                   f"{i}", callback_data=f'1|{i}'))

    await bot.send_message(message.chat.id,
                           "Какой адрес удалить:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
async def answer(call):
    """Обработка нажатия кнопки и запуск соответствующей функции"""
    result = call.data.split('|')
    if result[0] == '0':
        await check_mail_t(call.message, result[1])
    elif result[0] == '1':
        delete_mail_t(result[1])
        await bot.send_message(call.message.chat.id, f'{result[1]}, удалён')


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == '__main__':
    schedule.every(10).minutes.do(delete_old_records)

    Thread(target=schedule_checker).start()

    # Запускаем телеграм-бота
    print('SERVER START')
    asyncio.run(bot.polling(none_stop=True))
