import threading
import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import config
from client_classes.Message import Message


class VkClient:
    def __init__(self, compute_message_func):
        self.client = None
        self.upload = None
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
            return {"chat_settings": {"title": "NULL", "owner_id": "NULL"}}
        return chat["items"][0]

    def __get_photo(self, attachments):
        url = []
        for el in attachments:
            if el["type"] == "photo":
                for photo in el["photo"]["sizes"]:
                    if photo["type"] != "z":
                        continue

                    url.append(photo["url"])
                    break
            elif el["type"] == "doc" and el["doc"]["ext"] in config.PHOTO_EXT:
                url.append(el["doc"]["url"])
        return url

    def __handler(self):
        print("VK client started.")
        longpoll = VkBotLongPoll(self.client, self.group_id)

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                photo = self.__get_photo(event.object.message["attachments"])
                text = event.object.message["text"]
                author = self.__get_user(event.object.message["from_id"])
                author_id = event.object.message["from_id"]
                author_name = author["last_name"] + " " + author["first_name"]
                if event.from_chat:
                    from_id = event.chat_id
                    chat = self.__get_chat(event.chat_id)
                    chat_name = chat["chat_settings"]["title"]
                    is_owner = author_id == chat["chat_settings"]["owner_id"]
                    self.compute_massage(Message((from_id, "VK"), text, author_id, author_name, chat_name=chat_name, is_owner=is_owner, photos=photo))
                else:
                    from_id = event.object.message["from_id"]
                    self.compute_massage(Message((from_id, "VK"), text, author_id, author_name, photos=photo))

    def send_msg(self, id, text, photo, to_chat):
        files = []
        for i in range(len(photo)):
            out = open(config.TEMP_IMAGE_FOLDER + str(i) + ".jpg", "wb")
            out.write(requests.get(photo[i]).content)
            out.close()
            files.append(config.TEMP_IMAGE_FOLDER + str(i) + ".jpg")
        response = self.upload.photo_messages(photos=files, peer_id=self.__get_peer_id_by_id(id))

        attachment = ""
        for el in response:
            attachment += "photo" + str(el["owner_id"]) + "_" + str(el["id"]) + "_" + str(el["access_key"]) + ","
        attachment = attachment[:-1]

        if to_chat:
            self.client.method("messages.send", {"chat_id": id, "message": text, "attachment": attachment, "random_id": 0})
        else:
            self.client.method("messages.send", {"user_id": id, "message": text, "attachment": attachment, "random_id": 0})

    def run(self, token, group_id):
        self.client = vk_api.VkApi(token=token)
        self.upload = vk_api.VkUpload(self.client)
        self.group_id = group_id
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()
