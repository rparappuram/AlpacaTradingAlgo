import logging
from dotenv import load_dotenv
from strategy import sell_stocks, place_trailing_stop, buy_stocks
from slack_logger import get_slack_handler

load_dotenv()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
slack_handler = get_slack_handler()
logger.addHandler(slack_handler)


# Lambda handler function
def lambda_handler(event, context):
    """
    Lambda handler function
    """
    sell_stocks()
    place_trailing_stop()
    buy_stocks()

    return {
        "statusCode": 200,
        "body": "Trading strategy executed successfully",
    }


if __name__ == "__main__":
    lambda_handler(None, None)
