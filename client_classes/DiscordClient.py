import discord
import requests
import config
from client_classes.Message import Message


class DiscordClient(discord.Client):
    def __init__(self, compute_message_func):
        super(DiscordClient, self).__init__()
        self.compute_massage = compute_message_func

    def __get_photo(self, attachments):
        url = []
        for el in attachments:
            link = str(el)
            ext = link[link.rfind(".") + 1:]
            if ext in config.PHOTO_EXT:
                url.append(link)
        return url

    async def on_ready(self):
        print("DS client started.")

    async def on_message(self, message):
        if message.author != self.user:
            photo = self.__get_photo(message.attachments)
            from_id = message.channel.id
            text = message.content
            author_id = message.author.id
            author_name = message.author.name
            if type(message.channel) != discord.channel.DMChannel:
                chat_name = message.author.guild.name + "/" + message.channel.name
                is_owner = message.author.guild_permissions.administrator
                self.compute_massage(Message((from_id, "DS"), text, author_id, author_name, chat_name=chat_name, is_owner=is_owner, photos=photo))
            else:
                self.compute_massage(Message((from_id, "DS"), text, author_id, author_name, photos=photo))

    def send_msg(self, id, text, photo):
        files = []
        for i in range(len(photo)):
            out = open(config.TEMP_IMAGE_FOLDER + str(i) + ".jpg", "wb")
            out.write(requests.get(photo[i]).content)
            out.close()
            files.append(discord.File(config.TEMP_IMAGE_FOLDER + str(i) + ".jpg"))

        self.loop.create_task(self.get_channel(id).send(content=text, files=files))
