import discord
from client_classes.Message import Message


class DiscordClient(discord.Client):
    def __init__(self, compute_message_func):
        super(DiscordClient, self).__init__()
        self.compute_massage = compute_message_func

    async def on_message(self, message):
        if message.author != self.user:
            author_name = message.author.name
            chat_name = None
            if type(message.channel) != discord.channel.DMChannel:
                chat_name = message.author.guild.name + "/" + message.channel.name
            self.compute_massage(Message((message.channel.id, "DS"), message.content, message.author.id, author_name, chat_name))

    def send_msg(self, id, text):
        self.loop.create_task(self.get_channel(id).send(text))
