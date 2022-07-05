import config
from main_classes.UsersHandler import UsersHandler


def main():
    bot = UsersHandler(config.GRAPH_STORAGE_NAME, config.USERS_INFORMATION_DB_NAME, error_log_name=config.ERROR_LOG_NAME)
    bot.run(vk_token=config.VK_TOKEN, vk_group_id=config.VK_GROUP_ID, telegram_token=config.TELEGRAM_TOKEN, discord_token=config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
