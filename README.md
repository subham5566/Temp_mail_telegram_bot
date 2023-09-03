# Temp_mail_telegram_bot
Bot for creating temporary emails and receiving messages

.env.example
```
TOKEN = Enter the TOKEN of the telegram bot
```

# Start

```
pip install -r requirements.txt
```
```
python main.py
```

# Docker build

```
docker build . -t temp-mail
```

```
docker run -d temp-mail
```