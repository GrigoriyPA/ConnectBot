import threading
import telebot
from client_classes.Message import Message


class TelegramClient:
    def __init__(self, compute_message_func):
        self.client = None
        self.handler_thread = None
        self.compute_massage = compute_message_func

    def __handler(self):
        @self.client.message_handler(content_types=["text"])
        def on_message(message):
            author_name = message.from_user.last_name + " " + message.from_user.first_name
            chat_name = None
            if message.from_user.id != message.chat.id:
                chat_name = message.chat.title
            self.compute_massage(Message((message.chat.id, "TG"), message.text, message.from_user.id, author_name, chat_name))

        self.client.infinity_polling()

    def send_msg(self, id, text):
        self.client.send_message(id, text)

    def run(self, token):
        self.client = telebot.TeleBot(token)
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()
