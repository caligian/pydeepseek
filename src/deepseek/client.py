import base64
import sys
import os
import pandoc

from pyperclip import copy as write_clip

from openai import OpenAI
from openai import APIConnectionError
from openai import APIError

from .config import Config
from .utils import print_info, print_error, print_msg, tolist
from .stream import Stream
from .history import History

__all__ = ["Message", "Messages", "UploadError", "ResponseError", "Client"]

Message = dict[str, str | list[str] | list[dict[str, str]]]
Messages = list[Message]


class UploadError(Exception):
    pass


class ResponseError(Exception):
    pass


class Client:
    def __init__(self, config: Config, history: History) -> None:
        self.config = config
        self.history = history
        self.client: OpenAI = self.create_client()
        self.uploaded_files: list[dict[str, int | str]] = []
        self.images: list[str] = []
        self.cache: dict[str, str] = self.history.history

    def create_client(self) -> None:
        api_key_file = self.config.api_key_file
        api_key: str | None = None

        print_info(f"Reading API key from {api_key_file}")
        if not os.path.isfile(api_key_file):
            print_error("No API key provided")
            sys.exit(1)

        with open(api_key_file) as fh:
            api_key = fh.read().strip()

        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def input_image(self, filename: str) -> dict[str, str]:
        assert os.path.isfile(filename)
        b64_image_ext = filename.rsplit(".", maxsplit=2)[-1]

        with open(filename, "rb") as fh:
            b64_image = base64.b64encode(fh.read()).decode("utf-8")
            return {
                "type": "image_url",
                "image_url": {"url": f"data:image/{b64_image_ext};base64,{b64_image}"},
            }

    def input_text(self, query: str) -> dict[str, str]:
        return {"type": "text", "text": query}

    # Does not work with deepseek-chat
    def upload_data(self, filename: str, purpose="assistants") -> None:
        ext = filename.rsplit(".", maxsplit=2)

        assert os.path.isfile(filename)
        assert ext[-1] in ("txt", "jsonl", "csv")

        with open(filename, "rb") as file:
            try:
                response = self.client.files.create(file=file, purpose=purpose)
                self.uploaded_files.append(
                    dict(
                        filename=filename,
                        purpose=purpose,
                        id=response.id,
                        bytes=response.bytes,
                        created_at=response.created_at,
                    )
                )
                print_msg(
                    f"{filename}: File uploaded successfully! (size: {response.bytes})"
                )
            except FileNotFoundError:
                raise UploadError(f"Nonexistent file: {filename}")
            except APIConnectionError:
                raise APIConnectionError(
                    "API connection error. Please restart client",
                )
            except APIError:
                raise APIError("API Error. Please restart client")

    def input_data(self, filename: str) -> dict[str, str]:
        ext = filename.rsplit(".", maxsplit=2)

        assert os.path.isfile(filename)
        assert ext[-1] in ("txt", "jsonl", "csv")

        with open(filename, "r") as file:
            return {"type": "text", "text": file.read()}

    def markdown2org(self, s: str) -> str:
        s = s.replace("###", "#")
        try:
            md = pandoc.read(source=s, format="markdown")
            return pandoc.write(md, format="org")
        except KeyboardInterrupt:
            return s
        except EOFError:
            return s
        except Exception:
            return s

    def ask(
        self,
        question: str,
        stdout: bool = False,
        stream: bool = True,
        model: str = "deepseek-chat",
        reasoner: bool = False,
        max_tokens: int | None = None,
        clipboard: bool = False,
        images: str | list[str] | None = None,
        frequency_penalty: int | float = 0,
        presence_penalty: int | float = 0,
        top_p: int | float = 1.0,
        temperature: int | float = 1.0,
        files: list[str] | None = None,
        directive: str = "Use markdown format. For tables use a csv format. Do not use any text formatting such as boldface, italics, etc. Behave like a researchers who cites everything (possibly from google scholar), especially URLs. Always support evidence with cited data.",
    ) -> str:
        if out := self.cache.get(question):
            if clipboard:
                write_clip(out)

            if stdout:
                print(out)

            return out

        client = self.client
        model = "deepseek-reasoner" if reasoner else model
        max_tokens = 3000 if not max_tokens else max_tokens
        messages = [
            {"role": "system", "content": directive},
            {"role": "user", "content": [self.input_text(question)]},
        ]
        content = messages[1]["content"]

        if images:
            _ = [content.append(self.input_image(i)) for i in tolist(images)]

        # temporary workaround for client.files api
        if files:
            # TODO: Make sure files are data files according to deepseek
            _ = [content.append(self.input_data(f)) for f in tolist(files)]

        response_stream: Stream | None = None
        try:
            frequency_penalty = float(frequency_penalty) if frequency_penalty else None
            presence_penalty = float(presence_penalty) if presence_penalty else None
            presence_penalty = float(presence_penalty) if presence_penalty else None
            top_p = float(top_p) if top_p else None
            temperature = float(temperature) if temperature else None
            response_stream = Stream(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=stream,
                    max_tokens=max_tokens,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    top_p=top_p,
                    temperature=temperature,
                )
            )
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except EOFError:
            raise EOFError
        except APIConnectionError:
            raise APIConnectionError
        except APIError:
            raise APIError

        out: str = None
        if stdout:
            out = response_stream.print()
        else:
            out = response_stream.read()

        out = self.markdown2org(out)

        if clipboard:
            write_clip(out)

        self.cache[question] = out
        self.history.append(question, out)

        return out

    def close(self) -> None:
        if not self.client.is_closed():
            self.client.close()


Client.md2org = Client.markdown2org
