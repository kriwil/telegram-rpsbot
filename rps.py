from datetime import datetime
import hashlib
import json
import os
import time

import requests


TOKEN = os.environ.get('TELEGRAM_BOT_RPS_TOKEN')
BASE_URL = 'https://api.telegram.org/bot{token}'.format(token=TOKEN)
GET_UPDATES_URL = '{base}/getUpdates'.format(base=BASE_URL)
SEND_MESSAGE_URL = '{base}/sendMessage'.format(base=BASE_URL)
START_COMMAND = '/startrps'

ANSWERS = ['ROCK', 'PAPER', 'SCISSORS', 'SPOCK', 'LIZARD']

timestamp = time.time()
sessions = {}


def get_winner(first, second):
    first_index = ANSWERS.index(first.upper())
    second_index = ANSWERS.index(second.upper())
    diff = first_index - second_index
    mod = diff % 5
    if mod in [1, 3]:
        return 0
    elif mod in [2, 4]:
        return 1
    return None


class Session(object):

    def __init__(self, chat_id, session_id, first_person, second_person):
        self.chat_id = chat_id
        self.session_id = session_id
        self.first_person = first_person.replace('@', '')
        self.second_person = second_person.replace('@', '')
        self.answers = {}

    def is_answered(self):
        answered = [
            self.first_person in self.answers,
            self.second_person in self.answers,
        ]
        return all(answered)

    def answer(self, person, answer):
        if answer.upper() in ANSWERS:
            self.answers[person] = answer

    def person_has_answered(self, person):
        return person in self.answers

    def get_winner(self):
        first = self.answers[self.first_person].upper()
        second = self.answers[self.second_person].upper()

        people = [self.first_person, self.second_person]

        winner = get_winner(first, second)
        if winner:
            return people[winner]
        return None


def send_message(chat_id, message):
    data = {
        'chat_id': chat_id,
        'text': message,
    }
    requests.post(SEND_MESSAGE_URL, data=data)


def get_updates():
    response = requests.post(GET_UPDATES_URL)
    content = json.loads(response.content)

    parse_updates(content)


def parse_updates(updates):
    global timestamp

    for result in updates.get('result', []):
        _timestamp = result['message']['date']

        if _timestamp > timestamp:
            process_message(result['message'])
            timestamp = _timestamp


def process_message(message):
    text = message['text']
    if text.startswith(START_COMMAND):
        start_rps(message)
    elif 'username' in message['chat']:
        process_dm(message)


def process_dm(message):
    global sessions

    username = message['chat']['username']
    text = message['text']

    text_list = text.split(' ')
    session_id = text_list[0]
    if session_id in sessions:
        session = sessions[session_id]

        if session.person_has_answered(username):
            send_message(message['chat']['id'], "you have answered this")
            return

        answer = text_list[1]
        if answer.upper() in ANSWERS:
            send_message(message['chat']['id'], "you answered {answer}".format(answer=answer))
            session.answer(username, answer)

            if session.is_answered():
                winner = session.get_winner()
                for person, answer in session.answers.items():
                    send_message(session.chat_id, "@{} answered {}".format(person, answer))
                if winner:
                    send_message(session.chat_id, "@{} is the winner!".format(winner))
                else:
                    send_message(session.chat_id, "no winner, boohoo!")


def get_unique_session_id(chat_id, first_person, second_person):
    now = datetime.utcnow()
    session_id = "{}{}{}{}".format(chat_id, first_person, second_person, now.isoformat())
    return hashlib.sha1(session_id).hexdigest()[:8]


def start_rps(message):
    global sessions

    chat_id = message['chat']['id']
    text = message['text']
    _, first_person, second_person = text.split(' ')
    session_id = get_unique_session_id(chat_id, first_person, second_person)

    message = "match between {} and {}, to answer send 'code answer' directly to me"
    message = message.format(first_person, second_person)
    send_message(chat_id, message)

    message = "use the following code to send your choice ({}) e.g. '{} rock'. go!".format(
        ", ".join(map(lambda x: x.lower(), ANSWERS)),
        session_id)
    send_message(chat_id, message)
    send_message(chat_id, session_id)

    sessions[session_id] = Session(
        chat_id=chat_id, session_id=session_id, first_person=first_person, second_person=second_person)


def main():
    global timestamp

    while True:
        get_updates()
        time.sleep(1)


if __name__ == "__main__":
    main()
