import threading
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from client_classes.Message import Message


class VkClient:
    def __init__(self, compute_message_func):
        self.client = None
        self.group_id = None
        self.handler_thread = None
        self.compute_massage = compute_message_func

    def __get_peer_id_by_id(self, id):
        return id + 2000000000

    def __get_user(self, id):
        return self.client.method("users.get", {"user_ids": id})[0]

    def __get_chat(self, id):
        chat = self.client.method("messages.getConversationsById", {"peer_ids": self.__get_peer_id_by_id(id)})
        if chat["count"] == 0:
            return {"chat_settings": {"title": "NULL"}}
        return chat["items"][0]

    def __handler(self):
        longpoll = VkBotLongPoll(self.client, self.group_id)

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                author = self.__get_user(event.object["message"]["from_id"])
                author_name = author["last_name"] + " " + author["first_name"]
                chat_id = event.object["message"]["from_id"]
                chat_name = None
                if event.from_chat:
                    chat_id = event.chat_id
                    chat = self.__get_chat(event.chat_id)
                    chat_name = chat["chat_settings"]["title"]
                self.compute_massage(Message((chat_id, "VK"), event.object["message"]["text"], event.object["message"]["from_id"], author_name, chat_name))

    def send_msg(self, id, text, to_chat):
        if to_chat:
            self.client.method("messages.send", {"chat_id": id, "message": text, "random_id": 0})
        else:
            self.client.method("messages.send", {"user_id": id, "message": text, "random_id": 0})

    def run(self, token, group_id):
        self.client = vk_api.VkApi(token=token)
        self.group_id = group_id
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()
