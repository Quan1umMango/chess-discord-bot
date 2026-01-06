# Chess Discord Bot 

## Preview
https://github.com/user-attachments/assets/cf73967f-1163-468b-874a-ce78349c7a78

## Usage
Tested for Python 3.12.3

Clone the repo locally:
```git
git clone https://github.com/Quan1umMango/chess-discord-bot/
```

Downlaod the required dependencies:
```py
pip install -r requirements.txt
```

Create a .env file, and add these full these two strings:
```env
token = "YOUR_DISCORD_BOT_TOKEN_HERE"
testDBUri = "YOUR_MONGO_DB_URI_HERE" 
```

Then run the ``main.py`` file

 ## Project Structure 
``core`` contains the logic of the actual chess game.\
``bot`` contains the stuff related to the discord bot.\
``data`` contains code related to database
