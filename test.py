import asyncio
import inspect
import json
import logging
from asyncio import Queue, CancelledError
from typing import Text, Dict, Any, Optional, Callable, Awaitable, NoReturn

import requests
from rasa.core.channels.channel import (
    InputChannel,
    CollectingOutputChannel,
    UserMessage
)
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

logger = logging.getLogger(__name__)


class SecureRestInput(InputChannel):
    """
    A custom http input channel
    """
    @staticmethod
    def name(cls) -> Text:
        return "secure_rest"

    @staticmethod
    async def on_message_wrapper(
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
        text: Text,
        queue: Queue,
        seeder_id: Text,
        input_channel: Text,
        metadata: Optional[Dict[Text, Any]]
    ) -> None:
        collector = QueueOutputChannel(queue)
        message = UserMessage(
            text, collector, seeder_id, input_channel=input_channel, metadata=metadata
        )
        await on_new_message(message)
        await queue.put("DONE")

    @staticmethod
    async def _extract_seeder(req: Request) -> Optional[Text]:
        return req.json.get("seeder", None)

    @staticmethod
    async def _get_access_token(client, secret):
        data = {
            "client_id": client,
            "client_secret": secret,
            "audience": "http://localhost/webhooks/rest/webhook",
            "grant_type": "client_credentials",
        }
        url = "https://javis-be.us.auth0.com/oauth/token"
        response = requests.post(url, data)
        return response

    @staticmethod
    def _extract_message(req: Request) -> Optional[Text]:
        return req.json.get("message", None)

    def _extract_input_channel(self, req: Request) -> Text:
        return req.json.get("input_channel") or self.name()

    @staticmethod
    def _extract_headers(req: Request) -> Dict:
        client = req.headers.get("client_id")
        secret = req.headers.get("client_secret")
        return client, secret

    def stream_response(
            self,
            on_new_message: Callable[[UserMessage], Awaitable[None]],
            text: Text,
            seeder_id: Text,
            input_channel: Text,
            metadata: Optional[Dict[Text, Any]]
    ) -> Callable[[Any], Awaitable[None]]:
        async def stream(resp: Any) -> None:
            q = Queue()
            task = asyncio.ensure_future(
                self.on_message_wrapper(
                    on_new_message, text, q, seeder_id, input_channel, metadata
                )
            )
            while True:
                result = await q.get()
                if result == "DONE":
                    break
                else:
                    await resp.write(json.dumps(result) + "\n")
            await task

            return stream

        def blueprint(
                self, on_new_message: Callable[[UserMessage], Awaitable[None]]
        ) -> Blueprint:
            custom_webhook = Blueprint(
                "custom_webhook_{}".format(type(self).__name__),
                inspect.getmodule(self).__name__,
            )

            # noinspection PyUnusedLocal
            @custom_webhook.route("/", methods=["GET"])
            async def health(request: Request) -> HTTPResponse:
                return response.json({"status": "ok"})

            @custom_webhook.route("/webhook", methods=["POST"])
            async def receive(request: Request) -> HTTPResponse:
                client, secret = self._extract_headers(request)
                sender_id = await self._extract_sender(request)
                text = self._extract_message(request)
                input_channel = self._extract_input_channel(request)

                authorized = await self._get_access_token(client, secret)
                metadata = authorized.text
                if authorized.status_code == 200:
                    collector = CollectingOutputChannel()
                    # noinspection PyBroadException
                    try:
                        await on_new_message(
                            UserMessage(
                                text,
                                collector,
                                sender_id,
                                input_channel=input_channel,
                                metadata=metadata,
                            )
                        )
                    except CancelledError:
                        logger.error(
                            f"Message handling timed out for " f"user message '{text}'."
                        )
                    except Exception:
                        logger.exception(
                            f"An exception occured while handling "
                            f"user message '{text}'."
                        )
                    return response.json(collector.messages)
                else:
                    return response.json({"error": metadata})

            return custom_webhook


class QueueOutputChannel(CollectingOutputChannel):
    """
    Output Channel that collects and send messages in a list
    """

    @classmethod
    def name(cls) -> Text:
        return "queue"

    # noinspection PyMissingConstructor
    def __init__(self, message_queue: Optional[Queue] = None) -> None:
        super(QueueOutputChannel, self).__init__()
        self.messages = Queue if not message_queue else message_queue

    def latest_output(self) -> NoReturn:
        raise NotImplementedError("A queue doesn't allow to peek at message.")

    async def _persist_message(self, message: Dict[Text, Any]) -> None:
        await self.messages.put(message)
