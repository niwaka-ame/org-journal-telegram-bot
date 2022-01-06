import datetime
import telebot
from pathlib import Path
import re
import requests

journal_dir = Path("~/rakuen/journal/").expanduser()
picture_dir = journal_dir / "figs/"
token = input("API token: ")
bot = telebot.TeleBot(token)


@bot.message_handler(commands=["start"])
def greet(message):
    "Message to test connection."
    msg = "Hello, how are you?"
    bot.reply_to(message, msg)


@bot.message_handler(commands=["j"])
def create_journal(message):
    "Create a journal entry when command is /j."
    entryText = message.text.split("/j ", maxsplit=1)[-1]
    append_to_journal(entryText)
    bot.reply_to(message, f"Added current entry.")


def append_to_journal(text, future=None):
    """Append entry to journal.
    Input: future: datetime object.
    """

    if not future:
        time = datetime.datetime.now()
        time_HM = time.strftime("%H:%M")
    else:
        time = future
        time_HM = "todo".upper()  # Use todo keyword rather than time.

    filename = journal_dir / time.strftime("%Y-%m-%d.org")
    journal_title = time.strftime("%Y-%m-%d, %A")
    file_exists_flag = filename.exists()

    with open(filename, "a") as entry:
        if not file_exists_flag:
            # If file doesn't exist, create title.
            entry.write(f"* {journal_title}\n")
        entry.write(f"\n** {time_HM} ")
        headline, *body = text.splitlines()
        entry.write(headline)
        entry.write("\n")
        if future:
            # Create a timestamp
            entry.write(f"<{time.strftime('%Y-%m-%d %H:%M')}>\n")
        for line in body:
            entry.write(line)
            entry.write("\n")


@bot.message_handler(commands=["jf"])
def create_future_journal(message):
    "Create a future journal entry when command is /J."
    entryText = message.text.split("/jf ", maxsplit=1)[-1]
    splitEntry = entryText.split("\n", maxsplit=1)
    futureTime = time_parser(splitEntry[0])
    if isinstance(futureTime, str):  # If the parser doesn't return datetime
        bot.reply_to(message, futureTime)
        return None
    else:
        append_to_journal(splitEntry[-1], future=futureTime)
        bot.reply_to(message, "Added future event.")


def time_parser(text):
    """Parse future time. Input[td/tmr/weekday/date] + time.
    TODO add unit test.
    """

    # Constants
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    today_weekday = today.weekday()
    week = "sun, mon, tue, wed, thu, fri, sat".upper().split(", ")
    weekday_dict = {k: v for k, v in zip(week, range(7))}

    # Split text
    date_text = text.split(" ")[0].upper()
    # upper makes input case-insensitive
    if " " in text:
        try:
            time = datetime.datetime.strptime(text.split(" ")[-1], "%H:%M")
        except:
            return "Wrong datetime format."
    else:
        time = datetime.time(hour=0, minute=0)
        text_with_time = text + " 00:00"
        # Otherwise the parser won't work when format is numerical

    # Main parser
    if date_text in week:  # If date is a weekday
        weekday_num = weekday_dict[date_text]
        delta_day = (weekday_num - today_weekday) % 7
        if delta_day == 0:
            # If the weekday is the same as today, go for next week
            date = today + datetime.timedelta(days=7)
        else:
            # Find next weekday
            date = today + datetime.timedelta(days=delta_day)

    elif date_text == "TD":
        date = today

    elif date_text == "TMR":
        date = tomorrow

    elif re.search("^202[0-9][01][0-9][0-3][0-9]$", date_text):
        # If date is numerical
        try:
            result = datetime.datetime.strptime(text_with_time, "%Y%m%d %H:%M")
            return result
        except:
            return "Wrong datetime format."
    else:
        return "Wrong datetime format."

    result = datetime.datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=time.hour,
        minute=time.minute,
    )
    return result


@bot.message_handler(commands=["a"])
def get_agenda():
    """TODO Get org-agenda"""
    pass


@bot.message_handler(func=lambda m: True, content_types=["photo", "document"])
def get_photo(message):
    """
    Download photo sent from phone.
    Photos must be sent with captions starting with a random command.
    """
    if message.content_type == "photo":
        photo = message.photo[-1].file_id
    else:  # Full size photos are sent as document
        photo = message.document.file_id

    photo_file = bot.get_file(photo)
    # path = picture_dir / datetime.datetime.now().strftime(
    #    "tg_%Y%m%d_%H%M.jpg"
    # )
    file_name = message.caption.split(" ", maxsplit=1)[-1].replace(" ", "_") + ".jpg"
    path = picture_dir / file_name
    response = requests.get(
        "https://api.telegram.org/file/bot{0}/{1}".format(token, photo_file.file_path)
    )
    if response.status_code == 200:
        with open(path, "wb") as new_file:
            new_file.write(response.content)
    bot.reply_to(message, "Photo added!")


if __name__ == "__main__":
    bot.infinity_polling()
