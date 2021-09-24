import os # <-- just needed to import os
import server  # <-- imports the server.py file

my_secret = os.environ['Bot Token']

# This example requires the 'members' privileged intents

import discord
from discord.ext import commands
import random
from datetime import datetime

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True

PREFIX = '.'
bot = commands.Bot(command_prefix=PREFIX, description=description, intents=intents)

bot.prefix = PREFIX

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)

@bot.command(description='For when you wanna settle the score some other way')
async def choose(ctx, *choices: str):
    """Chooses between multiple choices."""
    await ctx.send(random.choice(choices))

@bot.command()
async def repeat(ctx, times: int, *, content):
    """Repeats a message multiple times.. up to 3 messages cause you guys are spammy"""
    # how do you repeat 0 or less times?
    if times < 1:
      raise ValueError('times should be >= 1')
    # if just once, just print it
    if times == 1:
      return await ctx.send(content)
    
    msg_i = 0
    # msg character limit is 2000
    max_msg_len = 1900
    n_times = 0
    # send 3 messages max
    max_msgs = 3
    while msg_i < max_msgs:
      msg_i += 1
      # start off w/ 1 line in the msg
      s = content
      n_times += 1
      # while we have characters left in the msg
      while len(s) < max_msg_len:  
        # if we've reached #times, then we done
        if n_times == times:
          return await ctx.send(s)
        
        # save what it was before so we can roll back
        prevs = s 
        # add a new line of content
        s += '\n' + content
        n_times += 1

        # if we over the character limit, roll back
        if len(s) >= max_msg_len:
          s = prevs
          n_times -= 1
          # send the message and start on the next one
          await ctx.send(s)
          break

@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    await ctx.send('{0.name} joined in {0.joined_at}'.format(member))

#### This was just a example of using command groups. I think it'd be better to do it the following way instead ####

# @bot.group()
# async def cool(ctx):
#     """Says if a user is cool.
#     """
#     # In reality this just checks if a subcommand is being invoked.
#     if ctx.invoked_subcommand is None:
#         await ctx.send('No, {} is not cool'.format(ctx.invoked_subcommand))

# @cool.command(name='bot')
# async def _bot(ctx):
#     """Is the bot cool?"""
#     await ctx.send('Yes, the bot is cool.')

@bot.command()
async def cool(ctx, member=None):
  """Says if a user is cool."""
  if member is None:
    member = ctx.message.author

  # if member was a mention, it would show up in here. 
  # we'll just grab the first one
  if ctx.message.mentions:
    member = ctx.message.mentions[0].display_name
  
  if member.lower() == 'bot':
    member = bot.user.display_name

  if member.lower() == bot.user.display_name.lower():
    await ctx.send('Yes, the bot is cool.')
    return

  await ctx.send('No, {} is not cool'.format(member))

@bot.command()
async def stinky(ctx):
  """The Stinky Command for your Friend!"""
  await ctx.send('you thought you could call someone stinky, but instead i will do it! you stinky.')

# example command from Red
@bot.command()
async def penis(ctx, user: discord.Member):
    """Detects user's penis length
    This is 100% accurate."""

    state = random.getstate()

    random.seed(user.id)
    dong = "8{}D".format("=" * random.randint(0, 30))

    random.setstate(state)
    msg = "{}'s size:\n{}\n".format(user.display_name, dong)

    await ctx.send(msg)

# this runs the web server
server.keep_alive()

bot.run(my_secret, reconnect=True) # <-- reconnects if it disconnects