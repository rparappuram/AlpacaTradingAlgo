from dotenv import load_dotenv

load_dotenv()
from config import trade_client
from strategy import sell_stocks, place_trailing_stop, buy_stocks


def lambda_handler(event, context):
    """
    Lambda handler function
    """
    clock = trade_client.get_clock()
    # if clock.is_open:
    sell_stocks()
    place_trailing_stop()
    buy_stocks()
    message = "Trading strategy executed successfully"
    # else:
        # message = "Market is closed"

    return {
        "statusCode": 200,
        "body": message,
    }


if __name__ == "__main__":
    lambda_handler(None, None)
