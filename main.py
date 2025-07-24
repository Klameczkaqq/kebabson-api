import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import os
import logging

from keep_alive import keep_alive 

keep_alive()  
bot.run(os.getenv("DISCORD_TOKEN"))
