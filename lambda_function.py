from dotenv import load_dotenv

load_dotenv()
from config import trade_client
from strategy import sell_stocks, place_trailing_stop, buy_stocks


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
