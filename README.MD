# Cover Letter Telegram Bot

The Cover Letter Bot helps you write a unique cover letter for each job application. Here are the steps:

* Send your CV in PDF or plain text format
	* In case you send a PDF file, the bot will parse it into plain text
* Send a link to the job description
	* The text from the job page will be parsed using beautifulsoup
* The text of your CV and job description will be sent to ChatGPT, which will return a cover letter.

You can try it on Telegram: `https://t.me/cover_letter_gpt_bot`.
If you have any questions, feel free to ask me at `tg:@zloypilgrim` or `mark.potanin@phystech.edu`

# Repository

This repository contains the full code for launching the Cover Letter Bot. I will describe the necessary steps below.

### 1. Create your new telegram bot.

To set up a new bot, you need to write to BotFather in Telegram - `@botfather`. Type the command `/newbot` to create a new bot. Once created, you will receive a unique token. Place this token in the variable `BOT_KEY` inside `main.py` on line 17. If you have trouble creating a new bot, read any tutorial (the first link in Google is [here](https://www.freecodecamp.org/news/how-to-create-a-telegram-bot-using-python/))

### 2. Get OpenAI API token.

* Go to `https://platform.openai.com/`
* Then go to `https://platform.openai.com/account/api-keys`,  or click the `View API keys` button in the upper right corner.
* reate a new key by clicking the `Create new secret key` button.
* Then use this API key inside `main.py` in the variable `openai.api_key` on line 16.

### 3. Cloud Server

After obtaining the Telegram API key and OpenAI API key, you can run your bot locally with `python main.py`. For production purposes, it's better to place the bot on a cloud server. I used `http://linode.com` (which offers a $100 trial period).

### 4. Service

Run your bot in the background on your cloud server. You can use my service file `cover_bot.service`.

* Place it in `/etc/systemd/system/cover_bot.service`.
* Don't forget to change: `User`, `WorkingDirectory` (path to cloned repo), and `ExecStart` (path to `main.py`). 
* Run your service with `systemctl start streamlit_app.service`. 

If you encounter any problems, read any tutorial about services (like [this](https://medium.com/codex/setup-a-python-script-as-a-service-through-systemctl-systemd-f0cc55a42267)).

