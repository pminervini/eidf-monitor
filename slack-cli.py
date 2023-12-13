import os
import config

import logging
logging.basicConfig(level=logging.DEBUG)

from utils import get_pods_not_using_gpus, filter_while_true_pods

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=config.SLACK_BOT_TOKEN)

@app.command("/check")
def handle_some_command(body, ack, respond, client, logger):
    ack()
    entry_lst = get_pods_not_using_gpus()
    for entry in entry_lst:
        respond(f'Pod {entry["pod"]} owned by {entry["owner"]} from {entry["namespace"]} was allocated [{entry["num_gpus"]}] GPUs but it is not using them.')
    logger.info(body)
    
    while_true_pods = filter_while_true_pods()
    for pod in while_true_pods:
        respond(f"Pod {pod['name']} using {pod['#GPUs']} GPUs was running for {pod['runtime']} with command {pod['command']}.")
    logger.info(body)

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

@app.event("app_mention")
def mention_handler(body, say):
    print(body)
    entry_lst = get_pods_not_using_gpus()
    for entry in entry_lst:
        say({"text": f'Pod {entry["pod"]} owned by {entry["owner"]} from {entry["namespace"]} was allocated [{entry["num_gpus"]}] GPUs but it is not using them.', "response_type": "in_channel"})

if __name__ == "__main__":
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()
