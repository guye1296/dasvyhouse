import telebot
import logging


def _read_secret(secret_file_name) -> str:
    try:
        with open(secret_file_name) as key_file:
            return key_file.read()
    except OSError as e:
        raise RuntimeError(str(e))


bot = telebot.TeleBot(_read_secret("api_key.secret"), parse_mode=None)


class Session:
    """
    A session to a bot given a chat id
    """
    ROOMS_NAMES = [
        u"למטה שירותים",
        u"למטה כביסה",
        u"למטה ארון",
        u"למעלה פרקט",
        u"למעלה לא פרקט",
    ]

    def __init__(self, chat_id):
        self._assignment = [8000/5] * 5
        self._chat_id = chat_id
        self._next = self._route
        self._quanta = 120

    def handle(self, message: telebot.types.Message):
        logging.info(f"{self._chat_id}: {message.text}")
        return self._next(message)

    def _route(self, message: telebot.types.Message):
        if message.text == '/usage':
            return self._usage(message)
        elif message.text == '/start':
            return self._usage(message)
        elif message.text == '/help':
            return self._usage(message)
        elif message.text == '/bid':
            return self._prompt_start_bid()
        elif message.text == '/quanta':
            return self._prompt_change_quanta()

    def _prompt_change_quanta(self):
        bot.send_message(self._chat_id, "Enter quanta")
        self._next = self._handle_quanta

    def _handle_quanta(self, message):
        try:
            self._quanta = int(message.text)
            self._next = self._route
        except ValueError:
            bot.send_message(self._chat_id, "Enter an actual number")

    def _prompt_start_bid(self):
        markup = telebot.types.ReplyKeyboardMarkup()
        buttons = [
            f"{amount}\n{self.ROOMS_NAMES[i]}" for i, amount in enumerate(self._assignment)
        ]
        markup.add(*buttons)

        bot.send_message(
            self._chat_id, f"Raise {self._quanta} shmekels to the following room", reply_markup=markup
        )
        self._next = self._handle_pick

    def _handle_pick(self, message: telebot.types.Message):
        if message.text == "/finish":
            self._next = self._route
            return
        if message.text == "/quanta":
            self._prompt_change_quanta()
            self._next = self._handle_quanta
            return

        selection = message.text.splitlines()[-1]

        if selection not in self.ROOMS_NAMES:
            bot.send_message(self._chat_id, f"room not valid")
            self._prompt_start_bid()
            return

        # raise 120 shmekels to room, and subtract from others
        for i in range(len(self.ROOMS_NAMES)):
            self._assignment[i] -= self._quanta / (len(self.ROOMS_NAMES) - 1)

        self._assignment[self.ROOMS_NAMES.index(selection)] += self._quanta + (self._quanta / (len(self.ROOMS_NAMES) - 1))
        self._prompt_start_bid()

    def _usage(self, message: telebot.types.Message):
        bot.reply_to(message, "Usage:\n"
                              "/bid : start bidding\n"
                              "/finish : finish bidding\n"
                              "/quanta : change quanta from 120\n"
                              "/help | /usage : show this message\n"
                     )


# TODO: terminate session after inactivity
_sessions = {}


@bot.message_handler()
def route_message(message: telebot.types.Message):
    # add to existing list of user sessions
    try:
        session = _sessions[message.chat.id]
    except KeyError:
        logging.info(f"Creating session {message.chat.id}")
        session = Session(message.chat.id)
        _sessions[message.chat.id] = session

    return session.handle(message)
