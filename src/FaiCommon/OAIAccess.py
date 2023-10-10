"""
Filename    :   OAIAccess.py
Copyright   :   FoundAItion Inc.
Description :   Access to OpenAI API
Written by  :   Alex Fedosov
Created     :   06/26/2023
Updated     :   07/19/2023
"""

from tenacity import retry, wait_random_exponential, stop_after_delay, \
    stop_after_attempt, retry_if_exception_type, retry_if_not_exception_type
from openai.error import TryAgain

import logging
import openai
import os
import time
import typing

log = logging.getLogger(__name__)


class OpenAIAccess():
    DEFAULT_TIMEOUT = 60  # sec
    MAX_FN_CALLS = 10

    INITIAL_FN_MESSAGES=[
        # to avoid hallucinated outputs in function calls
        {"role": "system", "content": "Only call the functions you have been provided with."},
        {"role": "system", "content": "Make a reasonable assumptions about what values to plug into functions if you can not deduce it from other function call."},

        # TODO(afedosov): interestingly enough this works well for gpt-3.5 model, but gpt-4 is taking
        # it more seriously and refuse many reqests as can not deduce arguments
        # {"role": "system", "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous or no arguments provided."},
    ]

    # if no function calling needed
    FN_DECLARATION_STUB = [
        {
            "name": "Noname",
            "parameters": {
                "type": "object",
                "properties": {
                    "stub": {
                        "type": "string",
                        "description": "",
                    },
                },
            },
        },
    ]

    # TODO(afedosov): add function name / arguments
    class CompletionResult(typing.NamedTuple):
        fn_called: bool = False
        usage_tokens: int = 0
        response: str = ""
        status: str = ""

    def __init__(self, completion_model, temperature, embedding_model) -> None:
        self.completion_model = completion_model
        self.embedding_model = embedding_model
        self.messages = []
        openai.organization = os.getenv("OPENAI_API_ORG")  # do we really need it? Seems ok without it.
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.set_temperature(temperature)

    def set_temperature(self, temperature):
        if temperature >= 0 and temperature <= 1:
            self.temperature = temperature
            return True
        log.debug(f"Temperature is out of range: {temperature}")
        return False

    def get_models(self):
        return openai.Model.list()

    def set_model(self, completion_model):
        self.completion_model = completion_model

    @retry(wait=wait_random_exponential(min=1, max=20), 
           stop=stop_after_attempt(3), 
           retry=retry_if_not_exception_type(openai.InvalidRequestError))
    def get_embedding(self, text):
        """Text embedding
        returns True/False, tokens, embedding, status
        """
        if not text:
            return False, 0, None, "Empty text"

        response = openai.Embedding.create(input=text, 
                                           model=self.embedding_model)
        embedding = ["data"][0]["embedding"]
        total_tokens = response["usage"]["total_tokens"]
        return True, total_tokens, embedding, ""

    def complete_with_fun(self, prompt, functions) -> CompletionResult:
        """Prompt completion with single function calling
        returns False, tokens, content, status for completetion or 
        returns True, tokens, func_name, func_args for function call

        Functions descriptions as JSON
        https://json-schema.org/understanding-json-schema/reference/array.html
        """
        self.messages.clear()
        self.messages.extend(OpenAIAccess.INITIAL_FN_MESSAGES)
        self.messages.append({"role": "user", "content": prompt})

        return OpenAIAccess.CompletionResult(self.__complete_with_fun(prompt, functions))


    def complete_with_multi_fun_array(self, prompt, functions) -> list[CompletionResult]:
        """Prompt completion with multiple function calling (generator)
        returns same as complete_with_fun()
        """
        self.messages.clear()
        self.messages.extend(OpenAIAccess.INITIAL_FN_MESSAGES)
        self.messages.append({"role": "user", "content": prompt})
        results = []

        for _ in range(OpenAIAccess.MAX_FN_CALLS):
            result = OpenAIAccess.CompletionResult(*self.__complete_with_fun(prompt, functions))
            results.append(result)

            if not result.fn_called:
                break

            # Don't do actual chaining - calling that function and adding 
            # call's result here, use complete_with_multi_fun generator for that
            self.messages.append({
                "role": "function", 
                "name": result.response,
                "content": "ok"
                })
        return results

    def complete_with_multi_fun(self, prompt, functions, keep_history) -> CompletionResult:
        """
        Prompt completion with multiple function calling (generator) or without any if functions is None.
        Can be provided with function call result for chaining, via send()
        """
        if not keep_history:
            self.messages.clear()
        
        # NB: Use this restrictive prompt with function calling ONLY, otherwise
        # this may limit response to "I don't know"!
        if functions:
            self.messages.extend(OpenAIAccess.INITIAL_FN_MESSAGES)
        self.messages.append({"role": "user", "content": prompt})

        for _ in range(OpenAIAccess.MAX_FN_CALLS):
            result = OpenAIAccess.CompletionResult(*self.__complete_with_fun(prompt, functions))
            fn_call_result = yield result

            if not result.fn_called:
                break

            # chain results to the next call
            if fn_call_result is not None and isinstance(fn_call_result, str):
                self.messages.append({
                    "role": "function", 
                    "name": result.response,
                    "content": fn_call_result
                    })
    
    # prompt with function calling private implementation
    def __complete_with_fun(self, prompt, functions) -> tuple((bool, int, str, str)):
        #@retry(retry=retry_if_exception_type(TryAgain),
        #       wait=wait_random_exponential(multiplier=1, max=40), 
        #       stop=stop_after_attempt(3))
        def CallChatCompletion():
            return openai.ChatCompletion.create(
                model=self.completion_model, 
                messages=self.messages,
                functions=functions if functions else OpenAIAccess.FN_DECLARATION_STUB,
                function_call="auto" if functions else "none",
                temperature=self.temperature,
                request_timeout=OpenAIAccess.DEFAULT_TIMEOUT  # undocumented
                # timeout= OpenAIAccess.DEFAULT_TIMEOUT doesn't really help
                )
            
        start_time = time.monotonic()
        response = CallChatCompletion()
        completion_time = time.monotonic() - start_time
        log.debug(f"Call complete: {self.completion_model} / {self.temperature:.2f}T / {completion_time:.2f} sec / {prompt}")

        if "choices" not in response:
            return False, 0, "", "Invalid response"

        if "message" not in response["choices"][0]:
            return False, 0, "", "Invalid message"
        
        message = response["choices"][0]["message"]
        total_tokens = response["usage"]["total_tokens"]

        # important - extend conversation with assistant's reply
        # otherwise it won't analyze prompt for additional function calls
        self.messages.append(message)

        # we can also check response['choices'][0]['finish_reason'] == 'function_call'
        if "function_call" not in message:
            return False, total_tokens, str(message.content), ""

        function_name = message["function_call"]["name"]
        arguments = message["function_call"]["arguments"]

        for function in functions:
            if "name" in function and function["name"] in function_name:
                # ****************** NOTE **********************
                # To fix Open AI issues with function naming: functions.ShowMeGraph, valid ShowMeGraph
                # which returned SOMETIMES we replace it back in the OpenAIObject,
                # so it's become valid in self.messages and resubmitted later back to OpenAI
                # conversation correctly, not throwing exception from OpenAI API
                #
                # <OpenAIObject at 0x240835c9a30> JSON: {
                #   "role": "assistant",
                #   "content": null,
                #   "function_call": {
                #     "name": "functions.ShowMeGraph",
                #     "arguments": "{\n  \"data\": [100, 200, 350, 50, 20],\n  \"style\": \"bar\"\n}"
                #   }                
                #
                message["function_call"]["name"] = function["name"]
                return True, total_tokens, function["name"], arguments

        return True, total_tokens, function_name, f"Unknown function called ({function_name})"

    def complete(self, prompt) -> tuple((int, str, str)):
        """Prompt completion
        """
        @retry(retry=retry_if_exception_type(TryAgain),
               wait=wait_random_exponential(multiplier=1, max=40), 
               stop=stop_after_attempt(3))
        def CallChatCompletion():
            return openai.ChatCompletion.create(
                model=self.completion_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                timeout= OpenAIAccess.DEFAULT_TIMEOUT
            )

        # Do not clear self.messages to keep context in the dialog
        start_time = time.monotonic()
        response = CallChatCompletion()
        completion_time = time.monotonic() - start_time

        log.debug(f"Call complete: {self.completion_model} / {completion_time:.2f} sec / {prompt}")

        if "choices" not in response or "usage" not in response:
            return 0, "", "Invalid response"

        if "message" not in response["choices"][0]:
            return 0, "", "Invalid message"

        return response["usage"]["total_tokens"], response.choices[0].message.content, ""


    def create_image(self, prompt, size="512x512", encoded=True) -> str:
        """
        Image creation, charged per API call, not tokens
        """
        @retry(retry=retry_if_exception_type(TryAgain),
               wait=wait_random_exponential(multiplier=1, max=40), 
               stop=stop_after_attempt(3))
        def CallImageCreate():
            return openai.Image.create(
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json" if encoded else "url" 
                )
        
        response = CallImageCreate()
        log.debug(f"Call complete: {prompt}")

        if "data" not in response:
            return ""

        data = response["data"][0]

        if encoded and "b64_json" in data:
            return data["b64_json"]
        
        if "url" in data:
            return data["url"]

        return ""
