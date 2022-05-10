import discord
from client_classes.Message import Message


class DiscordClient(discord.Client):
    def __init__(self, compute_message_func):
        super(DiscordClient, self).__init__()
        self.compute_massage = compute_message_func

    async def on_message(self, message):
        if message.author != self.user:
            from_id = message.channel.id
            text = message.content
            author_id = message.author.id
            author_name = message.author.name
            if type(message.channel) != discord.channel.DMChannel:
                chat_name = message.author.guild.name + "/" + message.channel.name
                is_owner = message.author.guild_permissions.administrator
                self.compute_massage(Message((from_id, "DS"), text, author_id, author_name, chat_name=chat_name, is_owner=is_owner))
            else:
                self.compute_massage(Message((from_id, "DS"), text, author_id, author_name))

    def send_msg(self, id, text):
        self.loop.create_task(self.get_channel(id).send(text))
