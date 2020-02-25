import logging.config
logging.config.fileConfig('logging.conf')


def main():
    from mixtape import updater, botfather_commandlist

    print(botfather_commandlist)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
