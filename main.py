import os
import asyncio
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, constants
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler
from telegram.ext import CallbackContext
from telegram.ext import filters
import glob
import shutil
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
import requests
import pdfplumber
import openai
import emoji

openai.api_key = "<YOUR OPENAI API KEY>"
BOT_KEY = "<YOUR TELEGRAM BOT KEY>"

CHOOSE_FORMAT, RECEIVE_PDF, RECEIVE_TEXT, RECEIVE_LINK = range(4)

HELPER = """
/start - to start a new conversation
If you want to upload new CV, also use a /start command
/cancel - to cancel conversation at any time

Use case:
1. Select format of your CV.
2. Send pdf file, or enter the text manually.
    * If text fits in one telegram message, just send text END as the second message.
3. Provide the link to job description. For example -  https://openai.com/careers/machine-learning-engineer-moderation
4. Wait for the response (could take it may take up to one minute, due to the load on the API).
5. The bot returns you a cover letter.
6. Send another job link, or use /done command to cancel the conversation.
"""


async def parse_pdf(filepath):
    text = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1)
            text.append(page_text)
    text = '\n'.join(text)
    return text


async def request_chatgpt(my_CV, link_to_job):
    cv_role = "You’re an assistant who helps to write cover letters for employers. I will send you my CV in plain text. You don't need answer to it, just remember and summarize it inside yourself."
    content_role = "You’re an assistant who helps to write cover letters and find job. I will send you job description. Based on information and requirements from employer, you have to write cover letter using my CV and align it with job description."

    page = requests.get(link_to_job)
    soup = BeautifulSoup(page.content, "html.parser")
    page_text = soup.get_text()

    completion = await sync_to_async(openai.api_resources.ChatCompletion.create)(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content":
                   cv_role},
                  {"role": "user", "content": my_CV},
                  {"role": "system", "content":
                   content_role},
                  {"role": "user", "content": page_text}  # link_to_job}

                  ]
    )

    result = completion.choices[0].message.content
    return result


async def start(update, context):

    user_id = update.message.from_user.id
    context.user_data.clear()
    options = [['pdf', 'Plain Text']]
    reply_markup = ReplyKeyboardMarkup(
        options, one_time_keyboard=True, resize_keyboard=True)
    # Send welcome message and ask user to choose format
    await update.message.reply_text("👋")
    await update.message.reply_text("Hi! I'm a cover letter bot. Please choose the format in which you want to submit your CV.", reply_markup=reply_markup)
    # Transition to CHOOSE_FORMAT state
    return CHOOSE_FORMAT


async def receive_format(update, context):
    # Get user's choice of format
    user = update.message.from_user
    cv_format = update.message.text.lower()
    chat_id = update.message.chat_id
    # Transition to appropriate state
    if cv_format == 'pdf':
        await update.message.reply_text('Please send me your CV in PDF format 📋:')
        await context.bot.send_document(chat_id, open('CV.pdf', 'rb'), caption='Here is an example of a resume that is parsed correctly.')
        return RECEIVE_PDF
    elif cv_format == 'plain text':
        await update.message.reply_text('Please enter your CV text ✍️:')
        await update.message.reply_text('NOTE: If your text fits only in one telegram message, just send text END as the second message.')
        return RECEIVE_TEXT
    else:
        update.message.reply_text(
            "I'm sorry, I didn't understand that. Please choose either PDF or Plain Text.",
            reply_markup=ReplyKeyboardMarkup(
                [["PDF", "Plain Text"]], one_time_keyboard=True, resize_keyboard=True,
            ),
        )

        return CHOOSE_FORMAT


async def receive_pdf(update, context):
    # Get user's PDF file
    user_id = update.message.from_user.id
    file_name = f'CVS/{user_id}.pdf'
    file_id = update.message.document.file_id

    file_obj = await context.bot.get_file(file_id)
    await file_obj.download_to_drive(file_name)
    reply_markup = ReplyKeyboardRemove()
    await update.message.reply_text('Thanks for sending me your CV!', reply_markup=reply_markup)

    text = await parse_pdf(file_name)
    # Transition to RECEIVE_LINK state
    await update.message.reply_text('Please send me a link to the job description:')

    context.user_data['cv_text'] = text
    return RECEIVE_LINK


async def receive_text(update, context):
    # Get user's text
    user_id = update.message.from_user.id
    text = update.message.text

    if 'cv_text' not in context.user_data:
        context.user_data['cv_text'] = text
        await update.message.reply_text('Please send me the rest of your CV text.')
        return RECEIVE_TEXT
    else:
        if not text == 'END':
            context.user_data['cv_text'] += '\n' + text

        file_name = f'CVS/{user_id}.txt'
        # Save text under user_id
        with open(file_name, 'w') as f:
            f.write(context.user_data['cv_text'])
        await update.message.reply_text('Thank you, I have received your CV.')
        await update.message.reply_text('Please send me a link to the job description:')

        return RECEIVE_LINK


async def receive_link(update, context):
    # Get user's job description link
    user_id = update.message.from_user.id
    link = update.message.text
    cv_text = context.user_data['cv_text']
    await update.message.reply_text('Thank you! Please wait, it may take up to 30 seconds 🕒')

    cover_letter_text = await request_chatgpt(cv_text, link)

    await update.message.reply_text(f'Here is your cover letter for the job at {link}:\n{cover_letter_text}')

    await update.message.reply_text("Please provide a new job link or type /done to exit.",
                                    reply_markup=ReplyKeyboardRemove(),
                                    )
    return RECEIVE_LINK


async def cancel(update, context):
    user_data = context.user_data
    user_data.clear()
    await update.message.reply_text(
        "You have canceled the conversation. "
        "Any previous input has been forgotten. "
        "Type /start to start again."
    )
    return ConversationHandler.END


async def done(update, context):
    user_data = context.user_data
    user_data.clear()
    await update.message.reply_text(
        "Thank you for using our bot. "
        "You can start a new conversation by typing /start."
    )
    return ConversationHandler.END


async def helper(update, context):
    await update.message.reply_text(text=HELPER, parse_mode=constants.ParseMode.HTML)


def main():

    application = Application.builder().token(BOT_KEY).build()
    # Set up ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_format)],
            RECEIVE_PDF: [MessageHandler(filters.Document.Category('application/pdf'), receive_pdf)],
            RECEIVE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
            RECEIVE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel),
                   CommandHandler("done", done)],
    )

    # Add ConversationHandler to Updater
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("help", helper))
    application.run_polling()
    print("Bot started!")


if __name__ == '__main__':
    main()
