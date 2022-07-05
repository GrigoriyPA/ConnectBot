import threading
import telebot
import requests
import config
from client_classes.Message import Message


class TelegramClient:
    def __init__(self, compute_message_func):
        self.token = None
        self.client = None
        self.handler_thread = None
        self.compute_massage = compute_message_func

    def __get_photo(self, message):
        if message.content_type == "photo":
            return ["https://api.telegram.org/file/bot" + self.token + "/" + self.client.get_file(message.photo[-1].file_id).file_path]
        elif message.content_type == "document":
            link = "https://api.telegram.org/file/bot" + self.token + "/" + self.client.get_file(message.document.file_id).file_path
            ext = link[link.rfind(".") + 1:]
            if ext in config.PHOTO_EXT:
                return [link]
        return []

    def __handler(self):
        print("TG client started.")

        @self.client.message_handler(content_types=["text", "photo", "document"])
        def on_message(message):
            photo = self.__get_photo(message)
            from_id = message.chat.id
            text = ""
            if message.content_type == "text":
                text = message.text
            elif message.caption is not None:
                text = message.caption
            author_id = message.from_user.id
            author = self.client.get_chat_member(from_id, author_id)
            author_name = message.from_user.last_name + " " + message.from_user.first_name
            if from_id != author_id:
                chat_name = message.chat.title
                is_owner = author.status == "creator"
                self.compute_massage(Message((from_id, "TG"), text, author_id, author_name, chat_name=chat_name, is_owner=is_owner, photos=photo))
            else:
                self.compute_massage(Message((from_id, "TG"), text, author_id, author_name, photos=photo))

        self.client.infinity_polling()

    def send_msg(self, id, text, photo):
        if photo == []:
            return self.client.send_message(id, text)

        self.client.send_photo(id, requests.get(photo[0]).content, caption=text)
        if len(photo) > 1:
            self.client.send_message(id, "Other photos:")
            for i in range(1, len(photo)):
                self.client.send_photo(id, requests.get(photo[i]).content)

    def run(self, token):
        self.token = token
        self.client = telebot.TeleBot(token)
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()
