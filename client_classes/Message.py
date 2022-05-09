class Message:
    def __init__(self, from_id, text, author_id, author_name, chat_name=None, is_owner=None):
        self.from_id = from_id
        self.text = text
        self.author_id = author_id
        self.author_name = author_name
        self.chat_name = chat_name
        self.is_owner = is_owner

    def is_chat_command(self):
        return len(self.text) > 0 and self.text[0] == "!"

    def get_chat_id(self):
        return str(self.from_id[0]) + self.from_id[1]

    def get_author_id(self):
        return str(self.author_id) + self.from_id[1]

    def get_chat_command(self):
        if not self.is_chat_command():
            return None
        return self.text[1:].strip()

    def get_text_to_forwarding(self):
        description = ""
        if self.author_name is not None:
            description += self.author_name + ":\n"
        return description + self.text
