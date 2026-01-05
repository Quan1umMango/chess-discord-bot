from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

test_uri = os.getenv("testDBUri")
uri = test_uri

client = MongoClient(uri, uuidRepresentation="standard")

# TODO: Add some sort of error handling
client.admin.command("ping")

chessdb = client["chess"]
