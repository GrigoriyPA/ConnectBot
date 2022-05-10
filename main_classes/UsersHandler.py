import threading
import sqlite3
import hashlib
import random
from main_classes.Graph import Graph
from client_classes.VkClient import VkClient
from client_classes.TelegramClient import TelegramClient
from client_classes.DiscordClient import DiscordClient


class UsersHandler:
    def __init__(self, graph_storage_name, users_information_db_name, token_length=1, error_log_name=None):
        self.error_log_name = error_log_name
        self.graph = Graph(graph_storage_name)
        self.select_chat = {"chat_name": None, "chat_id": (None, None)}
        self.token_length = token_length

        self.vk_client = VkClient(self.compute_message)
        self.discord_client = DiscordClient(self.compute_message)
        self.telegram_client = TelegramClient(self.compute_message)

        self.users_information_db_name = users_information_db_name
        conn = sqlite3.connect(users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, account_id INT);")
        cursor.execute("CREATE TABLE IF NOT EXISTS names(name TEXT PRIMARY KEY, account_id INT);")
        cursor.execute("CREATE TABLE IF NOT EXISTS accounts(account_id INT PRIMARY KEY, name TEXT, token TEXT, count INT);")
        conn.commit()

        self.free_id = 0
        cursor.execute("SELECT * FROM accounts;")
        for account in cursor.fetchall():
            self.free_id = max(self.free_id, account[0] + 1)

    def __create_token(self):
        token = ""
        for i in range(self.token_length):
            cur = random.randint(0, 63)
            if cur <= 9:
                token += str(cur)
            elif cur <= 35:
                token += chr(ord("a") + cur - 10)
            elif cur <= 61:
                token += chr(ord("A") + cur - 36)
            elif cur == 62:
                token += "_"
            else:
                token += "-"
        return token

    def __add_user(self, msg):
        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        if cursor.fetchone() is None:
            entry = (msg.get_author_id(), -1)
            cursor.execute("INSERT INTO users VALUES(?, ?);", entry)
            conn.commit()

    def __get_user_name(self, msg):
        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        info = cursor.fetchone()
        if info[1] == -1:
            return None
        cursor.execute("SELECT * FROM accounts WHERE account_id=" + str(info[1]) + ";")
        return cursor.fetchone()[1]

    def __is_login(self, msg):
        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        return cursor.fetchone()[1] != -1

    def __add_error_to_log(self, text):
        if self.error_log_name is not None:
            error_log = open(self.error_log_name, "a")
            error_log.write(text + "\n\n")
            error_log.close()

    def __send(self, id, text, to_chat=True):
        try:
            if id[1] == "VK":
                self.vk_client.send_msg(id[0], text, to_chat)
            elif id[1] == "DS":
                self.discord_client.send_msg(id[0], text)
            elif id[1] == "TG":
                self.telegram_client.send_msg(id[0], text)
            else:
                self.__add_error_to_log("Error: Unknown system to send message.")
        except Exception as error:
            self.__add_error_to_log("Error: Unknown error while sending the message.\nDescription:\n" + str(error))

    def __compute_command_select(self, msg):
        self.select_chat["chat_id"] = msg.from_id
        self.select_chat["chat_name"] = msg.chat_name
        self.__send(msg.from_id, "Chat is selected.")

    def __compute_command_connect(self, msg):
        select_id = self.select_chat["chat_id"]
        if select_id == (None, None):
            self.__send(msg.from_id, "Error: No selected chat.")
        elif select_id == msg.from_id:
            self.__send(msg.from_id, "Error: Attempting to connect a chat with itself.")
        elif select_id in self.graph.adjacency_list[msg.from_id]:
            self.__send(msg.from_id, "Error: Chats already connected.")
        else:
            self.graph.add_edge(msg.from_id, select_id)
            self.__send(msg.from_id, select_id[1] + " chat with name " + self.select_chat["chat_name"] + " is connected.")
            self.__send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is connected.")

    def __compute_command_disconnect(self, msg):
        select_id = self.select_chat["chat_id"]
        if select_id == (None, None):
            self.__send(msg.from_id, "Error: No selected chat.")
        elif not (select_id in self.graph.adjacency_list[msg.from_id]):
            self.__send(msg.from_id, "Error: Chats are not connected.")
        else:
            self.graph.erase_edge(msg.from_id, select_id)
            self.__send(msg.from_id, select_id[1] + " chat with name " + self.select_chat["chat_name"] + " is disconnected.")
            self.__send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is disconnected.")

    def __compute_command_create(self, msg):
        if self.__is_login(msg):
            return self.__send(msg.from_id, "To create a new account, you must log out of your current account.", to_chat=False)

        command = msg.text.split()
        if len(command) == 1:
            return self.__send(msg.from_id, "Error: To create an account, you need to provide an account name.", to_chat=False)
        name = " ".join(command[1:])

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM names WHERE name='" + name + "';")
        if cursor.fetchone() is not None:
            return self.__send(msg.from_id, "Error: An account with the name '" + name + "' already exists.", to_chat=False)

        cursor.execute("UPDATE users SET account_id=" + str(self.free_id) + " WHERE user_id='" + msg.get_author_id() + "';")
        entry = (name, self.free_id)
        cursor.execute("INSERT INTO names VALUES(?, ?);", entry)
        entry = (self.free_id, name, "?", 1)
        cursor.execute("INSERT INTO accounts VALUES(?, ?, ?, ?);", entry)
        conn.commit()
        self.free_id += 1
        self.__send(msg.from_id, "An account with the name '" + name + "' has been created.", to_chat=False)

    def __compute_command_login(self, msg):
        if self.__is_login(msg):
            return self.__send(msg.from_id, "To login, you must log out of your current account.", to_chat=False)

        command = msg.text.split()
        if len(command) == 1:
            return self.__send(msg.from_id, "Error: To enter an account, you need to provide a token.", to_chat=False)
        if len(command) == 2:
            return self.__send(msg.from_id, "Error: To enter an account, you need to provide an account name.", to_chat=False)
        token = command[1]
        name = " ".join(command[2:])

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM names WHERE name='" + name + "';")
        names_info = cursor.fetchone()
        if names_info is None:
            return self.__send(msg.from_id, "Error: There is no account with the name '" + name + "'.", to_chat=False)
        cursor.execute("SELECT * FROM accounts WHERE account_id=" + str(names_info[1]) + ";")
        account_info = cursor.fetchone()
        if account_info[2] == "?" or account_info[2] != hashlib.sha512(token.encode()).hexdigest():
            return self.__send(msg.from_id, "Error: Incorrect token.", to_chat=False)

        cursor.execute("UPDATE users SET account_id=" + str(account_info[0]) + " WHERE user_id='" + msg.get_author_id() + "';")
        cursor.execute("UPDATE accounts SET count=" + str(account_info[3] + 1) + " WHERE account_id=" + str(account_info[0]) + ";")
        conn.commit()
        self.__send(msg.from_id, "You are connected to the '" + name + "' account.", to_chat=False)

    def __compute_command_logout(self, msg):
        if not self.__is_login(msg):
            return self.__send(msg.from_id, "Error: Your account has not been logged in.", to_chat=False)

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        user_info = cursor.fetchone()
        cursor.execute("SELECT * FROM accounts WHERE account_id=" + str(user_info[1]) + ";")
        account_info = cursor.fetchone()

        cursor.execute("UPDATE users SET account_id=-1 WHERE user_id='" + msg.get_author_id() + "';")
        cursor.execute("UPDATE accounts SET count=" + str(account_info[3] - 1) + " WHERE account_id=" + str(account_info[0]) + ";")
        conn.commit()
        self.__send(msg.from_id, "You are disconnected from the account '" + account_info[1] + "'.", to_chat=False)
        if account_info[3] == 1:
            cursor.execute("DELETE FROM accounts WHERE account_id=" + str(account_info[0]) + ";")
            cursor.execute("DELETE FROM names WHERE name='" + str(account_info[1]) + "';")
            conn.commit()
            self.__send(msg.from_id, "Account '" + account_info[1] + "' has been deleted.", to_chat=False)

    def __compute_command_rename(self, msg):
        if not self.__is_login(msg):
            return self.__send(msg.from_id, "Error: Your account has not been logged in.", to_chat=False)

        command = msg.text.split()
        if len(command) == 1:
            return self.__send(msg.from_id, "Error: To rename an account, you need to provide an new account name.", to_chat=False)
        name = " ".join(command[1:])

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        user_info = cursor.fetchone()
        cursor.execute("SELECT * FROM names WHERE name='" + name + "';")
        if cursor.fetchone() is not None:
            return self.__send(msg.from_id, "Error: An account with the name '" + name + "' already exists.", to_chat=False)
        cursor.execute("SELECT * FROM accounts WHERE account_id=" + str(user_info[1]) + ";")
        account_info = cursor.fetchone()

        cursor.execute("UPDATE names SET name='" + name + "' WHERE name='" + account_info[1] + "';")
        cursor.execute("UPDATE accounts SET name='" + name + "' WHERE account_id=" + str(account_info[0]) + ";")
        conn.commit()
        self.__send(msg.from_id, "The account name has been changed from '" + account_info[1] + "' to '" + name + "'.", to_chat=False)

    def __compute_command_get_token(self, msg):
        if not self.__is_login(msg):
            return self.__send(msg.from_id, "Error: Your account has not been logged in.", to_chat=False)

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        user_info = cursor.fetchone()

        token = self.__create_token()
        cursor.execute("UPDATE accounts SET token='" + hashlib.sha512(token.encode()).hexdigest() + "' WHERE account_id=" + str(user_info[1]) + ";")
        conn.commit()
        self.__send(msg.from_id, "Token to connect to the account: " + token, to_chat=False)

    def __compute_command_delete_token(self, msg):
        if not self.__is_login(msg):
            return self.__send(msg.from_id, "Error: Your account has not been logged in.", to_chat=False)

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id='" + msg.get_author_id() + "';")
        user_info = cursor.fetchone()

        cursor.execute("UPDATE accounts SET token='?' WHERE account_id=" + str(user_info[1]) + ";")
        conn.commit()
        self.__send(msg.from_id, "The token for connecting to the account has been deleted.", to_chat=False)

    def __compute_chat_command(self, msg):
        command = msg.get_chat_command()
        if command == "select":
            self.__compute_command_select(msg)
        elif command == "connect":
            self.__compute_command_connect(msg)
        elif command == "disconnect":
            self.__compute_command_disconnect(msg)
        else:
            self.__send(msg.from_id, "Error: Unknown instruction.")

    def __compute_user_command(self, msg):
        self.__add_user(msg)
        command = msg.text.split()
        if len(command) >= 1 and command[0].lower() == "create":
            self.__compute_command_create(msg)
        elif len(command) >= 1 and command[0].lower() == "login":
            self.__compute_command_login(msg)
        elif len(command) >= 1 and command[0].lower() == "logout":
            self.__compute_command_logout(msg)
        elif len(command) >= 1 and command[0].lower() == "rename":
            self.__compute_command_rename(msg)
        elif len(command) >= 2 and command[0].lower() == "get" and command[1].lower() == "token":
            self.__compute_command_get_token(msg)
        elif len(command) >= 2 and command[0].lower() == "delete" and command[1].lower() == "token":
            self.__compute_command_delete_token(msg)
        else:
            self.__send(msg.from_id, "Error: Unknown instruction.", to_chat=False)

    def run(self, vk_token=None, vk_group_id=None, telegram_token=None, discord_token=None):
        if vk_token is not None and vk_group_id is not None:
            self.vk_client.run(vk_token, vk_group_id)
        if telegram_token is not None:
            self.telegram_client.run(telegram_token)
        if discord_token is not None:
            self.discord_client.run(discord_token)

    def compute_message(self, msg):
        if msg.text == "":
            return None

        if msg.chat_name is None:
            thread = threading.Thread(target=self.__compute_user_command, args=(msg, ))
            thread.start()
            return None

        self.graph.add_vertex(msg.from_id)
        if msg.is_chat_command():
            return self.__compute_chat_command(msg)

        name = self.__get_user_name(msg)
        if name is not None:
            msg.author_name = name
        for send_id in self.graph.get_reachable_vertices(msg.from_id):
            self.__send(send_id, msg.get_text_to_forwarding())
