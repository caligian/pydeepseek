from src.deepseek.client import Client
from src.deepseek.config import Config


client = Client(Config())
print(client.ask("Who painted the Mona Lisa?", stdout=False, stream=True))
