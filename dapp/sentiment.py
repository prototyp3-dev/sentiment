# Copyright 2023 Cartesi Pte. Ltd.
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


class Model:
    """
    Abstraction for a Machine Learning predictor model.
    """

    def __init__(self, filename: str='data/model.pkl'):
        """
        Model Initialization

        Parameters
        ----------
        filename : str
            File name for the pickled model
        """
        self._filename = filename
        self._model = None

    def load_model(self):
        """
        Load the model from file, if needed

        If the model is already loaded, this function will do nothing. It is
        therefore safe to call it multiple times.
        """
        if self._model is not None:
            return
        with open(self._filename, 'rb') as fin:
            self._model = pickle.load(fin)

    def predict(self, X: str) -> str:
        """
        Perform the model inference in a single sample and return the result.

        Parameters
        ----------
        X : str
            input sample

        Returns
        -------
        cls : str
            Output class
        """
        self.load_model()
        result = self._model.predict([X])
        return result[0]

MODEL = Model()


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
    sent = MODEL.predict(decoded_data)
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
    # Explicitly load model duringinitialization so it won't be done during
    # the processing of an advance_state message
    MODEL.load_model()

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
