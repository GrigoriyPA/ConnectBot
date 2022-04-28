import threading
import queue
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import discord
import telebot
import config


class Graph:
    def __init__(self, graph_storage_name):
        graph_storage = open(graph_storage_name, "r")
        self.graph_storage_name = graph_storage_name
        self.adjacency_list = dict()
        self.graph_storage_size = 0
        for line in graph_storage.readlines():
            type_operation, vertex1, vertex2 = self.__convert_text_to_operation(line)

            if type_operation == "+":
                self.add_edge(vertex1, vertex2, save_operation=False)
            else:
                self.erase_edge(vertex1, vertex2, save_operation=False)
            self.graph_storage_size += 1

    def __convert_text_to_operation(self, text):
        text = text.split()
        return text[0], (int(text[1]), text[2]), (int(text[3]), text[4])

    def __convert_operation_to_text(self, type_operation, vertex1, vertex2):
        return type_operation + " " + str(vertex1[0]) + " " + vertex1[1] + " " + str(vertex2[0]) + " " + vertex2[
            1] + "\n"

    def __reset_graph_storage(self):
        graph_storage = open(self.graph_storage_name, "w")
        used = set()
        self.graph_storage_size = 0
        for vertex1 in self.adjacency_list:
            for vertex2 in self.adjacency_list[vertex1]:
                if (vertex1, vertex2) in used or (vertex2, vertex1) in used:
                    continue

                used.add((vertex1, vertex2))
                graph_storage.write(self.__convert_operation_to_text("+", vertex1, vertex2))
                self.graph_storage_size += 1
        graph_storage.close()

    def __add_operation_to_storage(self, type_operation, vertex1, vertex2):
        graph_storage = open(self.graph_storage_name, "a")
        graph_storage.write(self.__convert_operation_to_text(type_operation, vertex1, vertex2))
        graph_storage.close()

        self.graph_storage_size += 1
        if self.graph_storage_size >= len(self.adjacency_list) ** 2:
            self.__reset_graph_storage()

    def get_reachable_vertices(self, vertex_start):
        used = set()
        used.add(vertex_start)
        q = queue.Queue()
        q.put(vertex_start)
        while not q.empty():
            v = q.get()
            for to in self.adjacency_list[v]:
                if to in used:
                    continue

                used.add(to)
                q.put(to)

        used.discard(vertex_start)
        return list(used)

    def add_vertex(self, vertex):
        if not (vertex in self.adjacency_list):
            self.adjacency_list[vertex] = set()

    def add_edge(self, vertex1, vertex2, save_operation=True):
        self.add_vertex(vertex1)
        self.add_vertex(vertex2)
        self.adjacency_list[vertex1].add(vertex2)
        self.adjacency_list[vertex2].add(vertex1)
        if save_operation:
            self.__add_operation_to_storage("+", vertex1, vertex2)

    def erase_edge(self, vertex1, vertex2, save_operation=True):
        if vertex1 in self.adjacency_list:
            self.adjacency_list[vertex1].discard(vertex2)
        if vertex2 in self.adjacency_list:
            self.adjacency_list[vertex2].discard(vertex1)
        if save_operation:
            self.__add_operation_to_storage("-", vertex1, vertex2)


class Message:
    def __init__(self, from_id, text, author_name, chat_name):
        self.from_id = from_id
        self.text = text
        self.author_name = author_name
        self.chat_name = chat_name

    def is_command(self):
        return len(self.text) > 0 and self.text[0] == "!"

    def get_command(self):
        if not self.is_command():
            return None
        return self.text[1:].strip().lower()

    def get_text_to_forwarding(self):
        description = ""
        if self.chat_name != None:
            description += " [" + self.chat_name + "]"
        if self.author_name != None:
            description += ", " + self.author_name
        if self.chat_name != None or self.author_name != None:
            description = self.from_id[1] + description + ":\n"
        return description + self.text


class VkClient:
    def __init__(self):
        self.vk_client = None
        self.group_id = None
        self.handler_thread = None

    def __get_user(self, id):
        return self.vk_client.method("users.get", {"user_ids": id})[0]

    def __get_chat(self, id):
        chat = self.vk_client.method("messages.getConversationsById", {"peer_ids": id + 2000000000})
        if chat["count"] == 0:
            return {"chat_settings": {"title": None}}
        return chat["items"][0]

    def __handler(self):
        longpoll = VkBotLongPoll(self.vk_client, self.group_id)

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                author = self.__get_user(event.object["message"]["from_id"])
                author_name = author["last_name"] + " " + author["first_name"]
                chat = self.__get_chat(event.chat_id)
                chat_name = chat["chat_settings"]["title"]
                compute_message(Message((event.chat_id, "VK"), event.object["message"]["text"], author_name, chat_name))

    def send_msg(self, id, text):
        self.vk_client.method("messages.send", {"chat_id": id, "message": text, "random_id": 0})

    def run(self, token, group_id):
        self.vk_client = vk_api.VkApi(token=token)
        self.group_id = group_id
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()


class TelegramClient:
    def __init__(self):
        self.telegram_client = None
        self.handler_thread = None

    def __handler(self):
        @self.telegram_client.message_handler(content_types=["text"])
        def on_message(message):
            author_name = message.from_user.last_name + " " + message.from_user.first_name
            chat_name = message.chat.title
            compute_message(Message((message.chat.id, "TG"), message.text, author_name, chat_name))

        self.telegram_client.infinity_polling()

    def send_msg(self, id, text):
        self.telegram_client.send_message(id, text)

    def run(self, token):
        self.telegram_client = telebot.TeleBot(token)
        self.handler_thread = threading.Thread(target=self.__handler)
        self.handler_thread.start()


class DiscordClient(discord.Client):
    async def on_message(self, message):
        if message.author != self.user:
            author_name = message.author.name
            chat_name = message.author.guild.name + "/" + message.channel.name
            compute_message(Message((message.channel.id, "DS"), message.content, author_name, chat_name))

    def send_msg(self, id, text):
        self.loop.create_task(discord_client.get_channel(id).send(text))


def add_error_to_log(text):
    error_log = open(config.ERROR_LOG_NAME, "a")
    error_log.write(text + "\n\n")
    error_log.close()


def send(id, text):
    try:
        if id[1] == "VK":
            vk_client.send_msg(id[0], text)
        elif id[1] == "DS":
            discord_client.send_msg(id[0], text)
        elif id[1] == "TG":
            telegram_client.send_msg(id[0], text)
        else:
            add_error_to_log("Error: Unknown system to send message.")
    except Exception as error:
        add_error_to_log("Error: Unknown error while sending the message.\nDescription:\n" + str(error))


def compute_command_select(msg):
    global select_chat

    select_chat["chat_id"] = msg.from_id
    select_chat["chat_name"] = msg.chat_name
    send(msg.from_id, "Chat is selected.")


def compute_command_connect(msg):
    global graph, select_chat

    select_id = select_chat["chat_id"]
    if select_id == (None, None):
        send(msg.from_id, "Error: No selected chat.")
    elif select_id == msg.from_id:
        send(msg.from_id, "Error: Attempting to connect a chat with itself.")
    elif select_id in graph.adjacency_list[msg.from_id]:
        send(msg.from_id, "Error: Chats already connected.")
    else:
        graph.add_edge(msg.from_id, select_id)
        send(msg.from_id, select_id[1] + " chat with name " + select_chat["chat_name"] + " is connected.")
        send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is connected.")


def compute_command_disconnect(msg):
    global graph, select_chat

    select_id = select_chat["chat_id"]
    if select_id == (None, None):
        send(msg.from_id, "Error: No selected chat.")
    elif not (select_id in graph.adjacency_list[msg.from_id]):
        send(msg.from_id, "Error: Chats are not connected.")
    else:
        graph.erase_edge(msg.from_id, select_id)
        send(msg.from_id, select_id[1] + " chat with name " + select_chat["chat_name"] + " is disconnected.")
        send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is disconnected.")


def compute_command(msg):
    command = msg.get_command()
    if command == "select":
        compute_command_select(msg)
    elif command == "connect":
        compute_command_connect(msg)
    elif command == "disconnect":
        compute_command_disconnect(msg)
    else:
        send(msg.from_id, "Error: Unknown instruction.")


def compute_message(msg):
    global graph

    if msg.text == "":
        return None

    graph.add_vertex(msg.from_id)
    if msg.is_command():
        return compute_command(msg)

    for send_id in graph.get_reachable_vertices(msg.from_id):
        send(send_id, msg.get_text_to_forwarding())


def main():
    global graph, select_chat, vk_client, discord_client, telegram_client

    graph = Graph(config.GRAPH_STORAGE_NAME)
    select_chat = {"chat_name": None, "chat_id": (None, None)}

    vk_client = VkClient()
    discord_client = DiscordClient()
    telegram_client = TelegramClient()

    vk_client.run(config.VK_TOKEN, config.VK_GROUP_ID)
    telegram_client.run(config.TELEGRAM_TOKEN)
    discord_client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
