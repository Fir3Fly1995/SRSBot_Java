import discord
from discord.ext import commands
import random
import httpx as aiohttp
from bs4 import BeautifulSoup
import asyncio
import os
import logging
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import certifi
import ssl
import queue
import time

print(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))

# Define the paths to the variable files
bot_items_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'SRSBot', 'Bot_Items')
token_file_path = os.path.join(bot_items_dir, 'token.txt')
channel_file_path = os.path.join(bot_items_dir, 'channel.txt')
roles_file_path = os.path.join(bot_items_dir, 'roles.txt')
cacert_path = os.path.join(bot_items_dir, 'cacert.pem')

# Read the bot token from the file
BOT_TOKEN = None
try:
    with open(token_file_path, 'r') as token_file:
        BOT_TOKEN = token_file.read().strip()
    logging.debug(f"Bot token read successfully: {BOT_TOKEN}")
except Exception as e:
    logging.error(f"Failed to read bot token: {e}")

# Read the welcome channel from the file
WELCOME_CHANNEL = None
try:
    with open(channel_file_path, 'r') as channel_file:
        WELCOME_CHANNEL = channel_file.read().strip()
    logging.debug(f"Welcome channel read successfully: {WELCOME_CHANNEL}")
except Exception as e:
    logging.error(f"Failed to read welcome channel: {e}")

# Read the roles from the file
P_VER_ROLE = None
VERIFIED_ROLE = None
try:
    with open(roles_file_path, 'r') as roles_file:
        roles = roles_file.readlines()
        if len(roles) > 0:
            P_VER_ROLE = roles[0].strip()
        if len(roles) > 1:
            VERIFIED_ROLE = roles[1].strip()
    logging.debug(f"P-Ver role read successfully: {P_VER_ROLE}")
    logging.debug(f"Verified role read successfully: {VERIFIED_ROLE}")
except Exception as e:
    logging.error(f"Failed to read roles: {e}")

# Ensure the bot token is a string
if not isinstance(BOT_TOKEN, str):
    logging.error(f"Invalid bot token type: {type(BOT_TOKEN)}")
    raise TypeError(f'expected token to be a str, received {type(BOT_TOKEN).__name__} instead')

intents = discord.Intents.default()
intents.message_content = True  # Enable reading message content

# Create the bot without the connector
bot = commands.Bot(command_prefix="!", intents=intents)

verification_codes = {}

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")
    logging.info(f'{bot.user} has connected to Discord!')

    try:
        await bot.tree.sync()  # Sync slash commands globally
        logging.info("Successfully synced slash commands globally")
    except Exception as e:
        logging.error(f"Error syncing slash commands: {e}")

@bot.tree.command(name="verify", description="Verify your RSI profile.")
async def verify_command(interaction: discord.Interaction, rsi_username: str = None):
    logging.debug(f"Received verify command from user: {interaction.user} with RSI username: {rsi_username}")
    await interaction.response.defer(ephemeral=True)  # Send an initial response to prevent timeout

    user_id = interaction.user.id

    if rsi_username is None:
        code = str(random.randint(100000, 999999))
        verification_codes[user_id] = code
        logging.debug(f"Generated verification code: {code} for user: {interaction.user}")

        await interaction.followup.send(
            f"{interaction.user.mention}, please enter the below code into the short bio field of your RSI profile found [here](https://robertsspaceindustries.com/en/account/profile). Return and do `/verify {interaction.user.name}` to complete the process.\n\n\n`{code}`",
            ephemeral=True
        )
        logging.info(f'Sent verification code to user: {interaction.user}')

    else:
        if user_id in verification_codes:
            code = verification_codes[user_id]
            try:
                url = f"https://robertsspaceindustries.com/en/citizens/{rsi_username}"
                logging.debug(f"Fetching RSI profile from URL: {url}")
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                        logging.debug(f"RSI profile fetched successfully for user: {interaction.user}")

                        soup = BeautifulSoup(await response.text(), "html.parser")
                        bio_element = soup.select_one("div.bio div.value")  # More specific CSS selector
                        if bio_element:
                            bio_text = bio_element.text.strip()
                            logging.debug(f"Bio text found: {bio_text}")
                            if code in bio_text:
                                verified_role = discord.utils.get(interaction.guild.roles, name=VERIFIED_ROLE)  # Gets the role object
                                p_ver_role = discord.utils.get(interaction.guild.roles, name=P_VER_ROLE)  # Gets the "P-Ver" role object
                                if verified_role and p_ver_role:
                                    await interaction.user.add_roles(verified_role)  # Gives the user the role
                                    await interaction.user.edit(nick=rsi_username)  # Change the user's nickname to match their RSI profile name
                                    logging.info(f'Attempted to change nickname for user {interaction.user} to {rsi_username}')

                                    await interaction.followup.send(f"Your nickname has been updated to: {rsi_username}. You have been verified. You can safely go ahead and remove the code from your profile now if you want to. Welcome to the SRS, Citizen!\n\nHead to <#{WELCOME_CHANNEL}> to get chatting!")
                                    logging.info(f'Sent verification success message to user: {interaction.user}')

                                    await asyncio.sleep(3)  # Wait for 3 seconds before removing the "P-Ver" role
                                    await interaction.user.remove_roles(p_ver_role)  # Removes the "P-Ver" role
                                    logging.info(f'Removed "P-Ver" role from user {interaction.user}')

                                    # await delete_messages_after(interaction, 1337856225022578719, delay=8)
                                else:
                                    await interaction.followup.send("Error: 'Verified' or 'P-Ver' role not found on this server.")
                                    logging.error(f"'Verified' or 'P-Ver' role not found on this server for user: {interaction.user}")
                                del verification_codes[user_id]  # Remove the code after successful verification
                                logging.debug(f"Removed verification code for user: {interaction.user}")
                            else:
                                await interaction.followup.send("Code not found in your RSI bio. Please double-check.", ephemeral=True)  # Ephemeral for errors too
                                logging.warning(f"Code not found in RSI bio for user: {interaction.user}")
                        else:
                            await interaction.followup.send("Could not find the bio section on your RSI profile. Please make sure your profile is public.", ephemeral=True)  # More informative message
                            logging.warning(f"Bio section not found on RSI profile for user: {interaction.user}")

            except aiohttp.ClientConnectorCertificateError as e:
                logging.error(f'Error checking RSI profile: {e}')
                await interaction.followup.send(f"Error checking RSI profile: {e}", ephemeral=True)
            except Exception as e:
                logging.error(f'An unexpected error occurred: {e}')
                await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)
        else:
            await interaction.followup.send("Please initiate the verification process by typing `/verify` first.", ephemeral=True)
            logging.warning(f"Verification process not initiated for user: {interaction.user}")

# Example function with logging
def example_function():
    try:
        logging.info("Starting example function")
        # Your code here
        logging.info("Example function completed successfully")
    except Exception as e:
        logging.error(f"Error in example function: {e}")

# Call the example function
example_function()

# Create a queue for thread-safe logging
log_queue = queue.Queue()

# Run the bot
async def run_bot():
    log_queue.put("run_bot function called")
    if BOT_TOKEN:
        log_queue.put("Starting the bot")
        await bot.start(BOT_TOKEN)
    else:
        log_queue.put("Bot token is None. Cannot start the bot.")

# Create the main window
logging.debug("Creating main window")
root = tk.Tk()
root.title("SRSBot Verifier")

# Create a console output window
logging.debug("Creating console output window")
console_output = ScrolledText(root, wrap=tk.WORD, width=100, height=20, font=("Helvetica", 10))
console_output.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

# Redirect logging to the console output window
class TextHandler(logging.Handler):
    def __init__(self, widget):
        logging.Handler.__init__(self)
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.widget.configure(state='normal')
            self.widget.insert(tk.END, msg + '\n')
            self.widget.configure(state='disabled')
            self.widget.yview(tk.END)
        self.widget.after(0, append)

logging.debug("Setting up logging to console output window")
text_handler = TextHandler(console_output)
logging.getLogger().addHandler(text_handler)

# Create a quit button
logging.debug("Creating quit button")
quit_button = tk.Button(root, text="Quit", command=root.quit)
quit_button.grid(row=1, column=1, padx=10, pady=10, sticky='e')

# Function to process log messages from the queue
def process_log_queue():
    while not log_queue.empty():
        msg = log_queue.get()
        logging.info(msg)
    root.after(100, process_log_queue)

# Start processing the log queue
root.after(100, process_log_queue)

# Run the bot in a separate thread
logging.debug("Starting bot thread")
threading.Thread(target=lambda: asyncio.run(run_bot())).start()

# Run the main loop
logging.debug("Starting main loop")
root.mainloop()
logging.debug("Main loop ended")