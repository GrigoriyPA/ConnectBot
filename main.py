import threading
import queue
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import discord
import telebot
import config


class DiscordClient(discord.Client):
    async def on_message(self, message):
        if message.author != self.user:
            compute_message((message.channel.id, "DS"), message.content)


def upload_graph_from_log():
    global graph, log_size

    file = open("log.txt", "r")
    graph = dict()
    log_size = 0
    for operation in file.readlines():
        log_size += 1
        desc = operation.split()
        ty, u, v = desc[0], (int(desc[1]), desc[2]), (int(desc[3]), desc[4])

        if not u in graph:
            graph[u] = set()
        if not v in graph:
            graph[v] = set()

        if ty == "+":
            graph[u].add(v)
            graph[v].add(u)
        else:
            graph[u].discard(v)
            graph[v].discard(u)


def reset_log():
    global graph, log_size

    file = open("log.txt", "w")
    used = set()
    log_size = 0
    for u in graph:
        for v in graph[u]:
            if (u, v) in used:
                continue

            used.add((u, v))
            used.add((v, u))
            file.write("+ " + str(u[0]) + " " + u[1] + " " + str(v[0]) + " " + v[1] + "\n")
            log_size += 1
    file.close()


def add_a_log_entry(text):
    global graph, log_size

    file = open("log.txt", "a")
    file.write(text)
    file.close()

    log_size += 1
    if log_size >= len(graph) * (len(graph) - 1):
        reset_log()


def send(id, text):
    if id[1] == "VK":
        vk_client.method("messages.send", {"chat_id": id[0], "message": text, "random_id": 0})
    elif id[1] == "DS":
        discord_client.loop.create_task(discord_client.get_channel(id[0]).send(text))
    elif id[1] == "TG":
        telegram_client.send_message(id[0], text)


def compute_message(id, msg):
    global graph, select_id

    if not id in graph:
        graph[id] = set()

    if len(msg) > 0 and msg[0] == "!":
        msg = msg[1:].strip()
        if msg.lower() == "select":
            select_id = id
            send(id, "Chat is selected.")
        elif msg.lower() == "connect":
            if select_id[0] == -1:
                send(id, "Error: No selected chat.")
            elif select_id == id:
                send(id, "Error: Attempting to connect a chat with itself.")
            elif select_id in graph[id]:
                send(id, "Error: Chats already connected.")
            else:
                graph[id].add(select_id)
                graph[select_id].add(id)
                send(id, select_id[1] + " chat with id " + str(select_id[0]) + " is connected.")
                send(select_id, id[1] + " chat with id " + str(id[0]) + " is connected.")
                add_a_log_entry("+ " + str(id[0]) + " " + id[1] + " " + str(select_id[0]) + " " + select_id[1] + "\n")
        elif msg.lower() == "disconnect":
            if select_id[0] == -1:
                send(id, "Error: No selected chat.")
            elif not select_id in graph[id]:
                send(id, "Error: Chats are not connected.")
            else:
                graph[id].discard(select_id)
                graph[select_id].discard(id)
                send(id, select_id[1] + " chat with id " + str(select_id[0]) + " is disconnected.")
                send(select_id, id[1] + " chat with id " + str(id[0]) + " is disconnected.")
                add_a_log_entry("- " + str(id[0]) + " " + id[1] + " " + str(select_id[0]) + " " + select_id[1] + "\n")
        else:
            send(id, "Error: Unknown instruction.")
    else:
        used = set()
        used.add(id)
        q = queue.Queue()
        q.put(id)
        while not q.empty():
            v = q.get()
            for to in graph[v]:
                if to in used:
                    continue

                send(to, msg)
                q.put(to)
                used.add(to)


def vk_handler():
    longpoll = VkBotLongPoll(vk_client, config.VK_GROUP_ID)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
            compute_message((event.chat_id, "VK"), event.object["message"]["text"])


def telegram_handler():
    @telegram_client.message_handler(content_types=["text"])
    def on_message(message):
        compute_message((message.chat.id, "TG"), message.text)

    telegram_client.infinity_polling()


log_size = 0
upload_graph_from_log()
select_id = (-1, "??")

vk_client = vk_api.VkApi(token=config.VK_TOKEN)
discord_client = DiscordClient()
telegram_client = telebot.TeleBot(config.TELEGRAM_TOKEN)

vk_t = threading.Thread(target=vk_handler)
telegram_t = threading.Thread(target=telegram_handler)

vk_t.start()
telegram_t.start()
discord_client.run(config.DISCORD_TOKEN)
