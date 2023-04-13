# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import logging
import requests
import pickle

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ.get("ROLLUP_HTTP_SERVER_URL", '')
logger.info(f"HTTP rollup_server url is {rollup_server}")

_MODEL = None
def get_model():
    """
    Load and cache the model.
    """
    global _MODEL

    if _MODEL is None:
        with open('data/model.pkl', 'rb') as fin:
            _MODEL = pickle.load(fin)

    return _MODEL


def classify_sentiment(text: str) -> str:
    """
    Perform the inference of a sentiment classifier on a given text.
    """
    model = get_model()
    result = model.predict([text])
    return result[0]


def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")

def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()

def handle_advance(data):
    logger.info(f"Received advance request data {data}")
    logger.info("Adding notice")

    decoded_data = hex2str(data['payload'])
    sent = classify_sentiment(decoded_data)
    logger.info("Inference of sentiment for '%s' is %s", decoded_data, sent)
    notice = {"payload": str2hex(sent)}

    response = requests.post(rollup_server + "/notice", json=notice)
    logger.info(f"Received notice status {response.status_code} body {response.content}")
    return "accept"

def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    logger.info("Adding report")
    report = {"payload": data["payload"]}
    response = requests.post(rollup_server + "/report", json=report)
    logger.info(f"Received report status {response.status_code}")
    return "accept"

handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}


def main_loop():
    finish = {"status": "accept"}
    rollup_address = None

    while True:
        logger.info("Sending finish")
        response = requests.post(rollup_server + "/finish", json=finish)
        logger.info(f"Received finish status {response.status_code}")
        if response.status_code == 202:
            logger.info("No pending rollup request, trying again")
        else:
            rollup_request = response.json()
            data = rollup_request["data"]
            if "metadata" in data:
                metadata = data["metadata"]
                if metadata["epoch_index"] == 0 and metadata["input_index"] == 0:
                    rollup_address = metadata["msg_sender"]
                    logger.info(f"Captured rollup address: {rollup_address}")
                    continue
            handler = handlers[rollup_request["request_type"]]
            finish["status"] = handler(rollup_request["data"])

if __name__ == '__main__':
    main_loop()
