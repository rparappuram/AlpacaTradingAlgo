import logging
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from io import StringIO

load_dotenv()


class SlackHandler(logging.Handler):
    def __init__(self, slack_token, slack_channel):
        logging.Handler.__init__(self)
        self.client = WebClient(token=slack_token)
        self.channel = slack_channel
        self.log_capture_string = StringIO()

    def emit(self, record):
        log_entry = self.format(record)
        self.log_capture_string.write(log_entry + "\n")

    def send_logs_to_slack(self):
        log_contents = self.log_capture_string.getvalue()
        if log_contents:
            try:
                response = self.client.chat_postMessage(
                    channel=self.channel, text=log_contents
                )
            except SlackApiError as e:
                print(f"Error sending log to Slack: {e.response['error']}")


def get_slack_handler():
    slack_token = os.getenv("SLACK_API_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL")
    slack_handler = SlackHandler(slack_token, slack_channel)
    slack_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    slack_handler.setFormatter(formatter)
    return slack_handler
