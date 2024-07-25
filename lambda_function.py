import logging
from dotenv import load_dotenv
from strategy import sell_stocks, place_trailing_stop, buy_stocks
from slack_logger import get_slack_handler

load_dotenv()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Stream handler for logging to STDOUT
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_formatter = logging.Formatter("%(message)s")
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)

# Slack handler for capturing logs and sending them to Slack
slack_handler = get_slack_handler()
logger.addHandler(slack_handler)


# Lambda handler function
def lambda_handler(event, context):
    """
    Lambda handler function
    """
    try:
        sell_stocks()
        place_trailing_stop()
        buy_stocks()

        return {
            "statusCode": 200,
            "body": "Trading strategy executed successfully",
        }
    finally:
        slack_handler.send_logs_to_slack()


if __name__ == "__main__":
    lambda_handler(None, None)
