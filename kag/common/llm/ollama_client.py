# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import logging
from ollama import Client, AsyncClient

from kag.interface import LLMClient


# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@LLMClient.register("Ollama")
@LLMClient.register("ollama")
class OllamaClient(LLMClient):
    """
    A client class for interacting with the Ollama API.

    This class provides methods to make synchronous requests to the Ollama API, handle model calls, and parse responses.
    """

    def __init__(
        self,
        model: str,
        base_url: str = None,
        timeout: float = None,
        max_rate: float = 1000,
        time_period: float = 1,
        stream: bool = False,
        **kwargs,
    ):
        """
        Initializes the OllamaClient instance.

        Args:
            model (str): The model to use for requests.
            base_url (str): The base URL for the Ollama API.
            timeout (float): The timeout duration for the service request. Defaults to None, means no timeout.
        """
        name = kwargs.pop("name", None)
        if not name:
            name = f"{base_url}{model}"

        super().__init__(name, max_rate, time_period, **kwargs)
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.stream = stream
        self.param = {}
        self.client = Client(host=self.base_url, timeout=self.timeout)
        self.aclient = AsyncClient(host=self.base_url, timeout=self.timeout)
        self.check()
        logger.debug(
            f"Initialize OllamaClient with rate limit {max_rate} every {time_period}s"
        )

    def __call__(self, prompt: str = "", image_url: str = None, **kwargs):
        """
        Executes a model request when the object is called and returns the result.

        Parameters:
            prompt (str): The prompt provided to the model.

        Returns:
            str: The response content generated by the model.
        """
        # Call the model with the given prompt and return the response
        reporter = kwargs.get("reporter", None)
        segment_name = kwargs.get("segment_name", None)
        tag_name = kwargs.get("tag_name", None)

        tools = kwargs.get("tools", None)
        messages = kwargs.get("messages", None)
        if messages is None:
            if image_url:
                messages = [
                    {"role": "system", "content": "you are a helpful assistant"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ]
            else:
                messages = [
                    {"role": "system", "content": "you are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ]
        response = self.client.chat(
            model=self.model,
            messages=messages,
            stream=self.stream,
            tools=tools,
        )
        if not self.stream:
            # reasoning_content = getattr(
            #     response.choices[0].message, "reasoning_content", None
            # )
            # content = response.choices[0].message.content
            # if reasoning_content:
            #     rsp = f"{reasoning_content}\n{content}"
            # else:
            #     rsp = content
            rsp = response["message"]["content"]
            tool_calls = response["message"].get("tool_calls", None)
        else:
            rsp = ""
            tool_calls = None  # TODO: Handle tool calls in stream mode

            for chunk in response:
                if chunk["message"]["content"] is not None:
                    rsp += chunk["message"]["content"]
                    if reporter:
                        reporter.add_report_line(
                            segment_name,
                            tag_name,
                            rsp,
                            status="RUNNING",
                        )
        # Remove <think> </think> blocks from the response
        if "<think>" in rsp and "</think>" in rsp:
            think_start = rsp.find("<think>")
            think_end = rsp.find("</think>") + len("</think>")
            rsp = rsp[:think_start] + rsp[think_end:]
            # Clean up any extra whitespace that might be left
            rsp = rsp.strip()
        if reporter:
            reporter.add_report_line(
                segment_name,
                tag_name,
                rsp,
                status="FINISH",
            )
        if tools and tool_calls:
            return response.message
        return rsp

    async def acall(self, prompt: str = "", image_url: str = None, **kwargs):
        """
        Executes a model request when the object is called and returns the result.

        Parameters:
            prompt (str): The prompt provided to the model.

        Returns:
            str: The response content generated by the model.
        """
        # Call the model with the given prompt and return the response
        reporter = kwargs.get("reporter", None)
        segment_name = kwargs.get("segment_name", None)
        tag_name = kwargs.get("tag_name", None)

        tools = kwargs.get("tools", None)
        messages = kwargs.get("messages", None)
        if messages is None:
            if image_url:
                messages = [
                    {"role": "system", "content": "you are a helpful assistant"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ]
            else:
                messages = [
                    {"role": "system", "content": "you are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ]
        response = await self.aclient.chat(
            model=self.model,
            messages=messages,
            stream=self.stream,
            tools=tools,
        )
        if not self.stream:
            # reasoning_content = getattr(
            #     response.choices[0].message, "reasoning_content", None
            # )
            # content = response.choices[0].message.content
            # if reasoning_content:
            #     rsp = f"{reasoning_content}\n{content}"
            # else:
            #     rsp = content
            rsp = response.message.content
            tool_calls = response.message.tool_calls
        else:
            rsp = ""
            tool_calls = None  # TODO: Handle tool calls in stream mode

            async for chunk in response:
                if chunk.message.content is not None:
                    rsp += chunk.message.content
                    if reporter:
                        reporter.add_report_line(
                            segment_name,
                            tag_name,
                            rsp,
                            status="RUNNING",
                        )
        if reporter:
            reporter.add_report_line(
                segment_name,
                tag_name,
                rsp,
                status="FINISH",
            )
        if tools and tool_calls:
            return response.message
        return rsp


if __name__ == "__main__":
    client = OllamaClient(
        model="qwen2.5:7b", base_url="http://localhost:11434", stream=True
    )
    print(client("你好"))
