import os
import utils
import requests
import logging

import slack
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.adapter.socket_mode import SocketModeHandler

from construct_API_Params import BigboxParams
from ParamBot import ParamBot
from ProductBot import ProductBot
import messages


# Create a logger object
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('logfile.log')
stream_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Global Variables
START_TIME = 0


# Use App_Mention event to indicate the start of a new product query.
bigboxParams = BigboxParams()
paramBot = ParamBot()

#Event Handlers

@app.event("member_joined_channel")
def welcome_message(event, say):
    # say(messages.WELCOME_MESSAGE.format(user=event['user']), channel=event['channel'])
    channel = event["channel"]
    print(channel)
    welcome_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Welcome! :ghost: I'm a shopping assistant that will try my best to help you find what you need at Home Depot. \n\n :book: *Instructions* \n 1. Always mention me (@MentionBot) to start a new query. I will guide you through constructing a search query on the products you are insterested in*.  \n 2. I will then show what I find about the products of your interests, and I can answer any questions that you might have. \n\n *I'm still learning, and I might make mistakes. :robot_face: So here is the shortcut -- if you send me a message in JSON format as following, I will be gathering all relevant information. \n {\n \"search_term\": \"some product\", \n \"max_price\": \"100\", \n \"sort_by\": \"best_seller\" \n} \n where _*sort_by*_ can be one of \"_best_seller_\", \"_most_popular_\", \"_price_high_to_low_\", \"_price_low_to_high_\", \"_highest_rating_\", and _*max_price*_ indicates the maximum budget you have for the product."
                }
            }
        ]

    try:
        response = client.chat_postMessage(
            channel=channel,
            text="a welcome message.",
            blocks = welcome_blocks
                )
        return response
    except SlackApiError as e:
        print(f"Error sending message when sending a welcome message: {e.response['error']}")

@app.event("app_mention")
def event_test(event, say, context):

    bot_id = f"<@U058G072QDU>"
    utils.set_state("IS_PRODUCT_BOT", 0)

    # Ignore messages that have extra text
    if event['text'].strip() == bot_id:
        say(messages.MENTION_MESSAGE)


@app.message(".*")
def message_handler_chat(message, say, context, logger):

    print(utils.get_state('IS_PRODUCT_BOT'))

    bot_id = f"<@U058G072QDU>"

    # FIX: What if the user asks a question.
    if message['text'].strip() == bot_id:
        return

    # Need to fix this.
    if "{" in message['text']:
        ask_confirmation(message['channel'])
        return

    # Use chatGPT for other messages
    if not utils.get_state("IS_PRODUCT_BOT"):
        output = paramBot.predict(message['text'])
    else:
        productBot = ProductBot(utils.get_state('curr_product'))
        output = productBot.predict(message['text'])
    say(output)


# Send a message with buttons to the user
def ask_confirmation(channel):

    try:
        response = client.chat_postMessage(
            channel=channel,
            text="a placeholder text.",
            blocks = [
             {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Just to double check, does it look correct?"
                }
            },
            {
                "type": "actions",
                # "block_id": "",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text", "text": "Yes"},
                        "style": "primary",
                        "value": "no",
                        "action_id": "confirm_action",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "No"},
                        "style": "primary",
                        "value": "no",
                        "action_id": "cancel_action",
                    }
                ]
            }
                ]
                )
        return response
    except SlackApiError as e:
        print(f"Error sending message when asking for product confirmation: {e.response['error']}")


# Handle user's response to the question
@app.action("cancel_action")
def handle_cancel_action(ack, body, say):
    # Acknowledge the button click event
    ack()
    
    # Process the user's cancellation
    print("User cancelled")
    say(messages.CANCEL_ACTION)

@app.action("confirm_action")
def handle_confirm_action(ack, body, say, context):
    # Acknowledge the button click event
    ack()

    say(messages.CONFIRM_ACTION)
    send_api_request(body, say, context)

    # Process the user's confirmation
    print("User confirmed")

def send_api_request(body, say, context):
    message = retrieve_last_messages(body['channel']['id'])
    print(message)
    try:
        if "{" in message:
            start_index = message.index("{")
            end_index = message.index("}")
            input_string = message[start_index:end_index+1]
            input_string = input_string.strip() 
            print(input_string)
            
            params = bigboxParams.construct_params(input_string)
            # make the http GET request to the BigBox API
            api_result = requests.get('https://api.bigboxapi.com/request', params)
            # save the JSON response to a local file using the save_json_response function from the utils file
            utils.save_json_response(api_result.json(), params['search_term'])
            if utils.check_success_from_json_file(params['search_term']):
                say(messages.PRODUCT_RECEIVED)
                utils.set_state("example_index", 0)
                show_product_examples(body['channel']['id'], params['search_term'])
                utils.set_state("IS_PRODUCT_BOT", 1)
                utils.set_state("curr_product", params['search_term'])
                
        else:
            say(messages.PRODUCT_ERROR)
    except Exception as e:
        say(f"An error occurred while sending API request: {str(e)}")

def show_product_examples(channel, search_term):
    """
    A function that show a few examples from the search.
    """

    products = utils.get_products(search_term)

    blocks = []

    title_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are a few examples."
                }
            }

    blocks.append(title_block)

    # Show product examples.
    for product in products:
        block = {
                "type": "section",
                # "block_id": "product_detail",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{product['url']}|{product['title']}> \n *Price:* ${product['price']} \n *Rating:* {product['rating']} ({product['ratings_total']} total ratings)"
                },
                "accessory": {
                    "type": "image",
                    "image_url": f"{product['image_url']}",
                    "alt_text": f"{product['title']}"
                }
        }

        blocks.append(block)

    # Show more examples or ask specific questions.
        more_example_text = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Want more examples?"
            }
        }
        more_example_choices = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text", "text": "Yes, please!"},
                    "style": "primary",
                    "value": search_term,
                    "action_id": "confirm_more_example",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "No, thanks."},
                    "style": "primary",
                    "value": "no",
                    "action_id": "no_more_example",
                }
            ]
        }

        blocks.extend([more_example_text, more_example_choices])

    try:
        response = client.chat_postMessage(
            channel=channel,
            text="Example products.",
            blocks = blocks
                )
        return response
    except SlackApiError as e:
        print(f"Error sending message when sending example products: {e.response['error']}")    

# Handle user's response to more examples.
@app.action("no_more_example")
def handle_cancel_action(ack, body, say):
    # Acknowledge the button click event
    ack()
    
    # Process the user's cancellation
    print("No more examples.")
    say(messages.NO_MORE_EXAMPLES)

@app.action("confirm_more_example")
def handle_confirm_action(ack, body, say, context):
    # Acknowledge the button click event
    ack()

    show_more_examples(body['channel']['id'], body['actions'][0]['value'])
    say(messages.SHOWED_MORE_EXAMPLES)

    # Process the user's confirmation
    print("Want more examples.")

def show_more_examples(channel, search_term):

    # Add a state variable to track product examples.
    products = utils.get_products(search_term)

    blocks = []

    title_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are more products for you to choose from."
                }
            }

    blocks.append(title_block)

    # Show product examples.
    for product in products:
        block = {
                "type": "section",
                # "block_id": "product_detail",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{product['url']}|{product['title']}> \n *Price:* ${product['price']} \n *Rating:* {product['rating']} ({product['ratings_total']} total ratings)"
                },
                "accessory": {
                    "type": "image",
                    "image_url": f"{product['image_url']}",
                    "alt_text": f"{product['title']}"
                }
        }

        blocks.append(block)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text="Example products.",
            blocks = blocks
                )
        return response
    except SlackApiError as e:
        print(f"Error sending message when sending example products: {e.response['error']}")    


# Function to retrieve the last one or two messages
def retrieve_last_messages(channel_id):
    try:
        response = client.conversations_history(
            channel=channel_id,
            oldest="0",  # Set the oldest parameter to "0" to retrieve the most recent messages
            inclusive=True,
            limit=3
        )
        messages = response["messages"]

        return messages[2]['text'] #FIX: cannot hardcode.
        
    except Exception as e:
        print(f"Error retrieving messages: {str(e)}")


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
