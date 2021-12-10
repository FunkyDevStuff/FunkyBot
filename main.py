import os # <-- just needed to import os
import server  # <-- imports the server.py file

my_secret = os.environ['Bot Token']
owner_id = int(os.environ['owner_id'])

# This example requires the 'members' privileged intents

import discord
from discord.ext import commands
from replit import db
from copy import deepcopy
import traceback
import random
from datetime import datetime, timedelta
import re

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True

PREFIX = '.'
bot = commands.Bot(command_prefix=PREFIX, description=description, intents=intents, owner_id=owner_id)

bot.prefix = PREFIX


BOT_DEFAULT_SETTINGS = {'admin_role': None}

if 'BOT_SETTINGS' not in db.keys():
  db['BOT_SETTINGS'] = deepcopy(BOT_DEFAULT_SETTINGS)

bot_settings = deepcopy(db['BOT_SETTINGS'])


QUEST_DEFAULT_SETTINGS = {'quest_master_role': None}

if 'QUEST_SETTINGS' not in db.keys():
  db['QUEST_SETTINGS'] = deepcopy(QUEST_DEFAULT_SETTINGS)

quest_settings = deepcopy(db['QUEST_SETTINGS'])

# handle command errors
async def on_command_error(ctx, error, unhandled_by_cog=False):
  if not unhandled_by_cog:
    if hasattr(ctx.command, "on_error"):
      return

    if ctx.cog:
      if ctx.cog.has_error_handler():
        return

  if isinstance(error, commands.MissingRequiredArgument):
    await ctx.send_help(ctx.command)
  elif isinstance(error, commands.ArgumentParsingError):
    msg = "`{user_input}` is not a valid value for `{command}`".format(
        user_input=error.user_input, command=error.cmd
    )
    if error.custom_help_msg:
      msg += f"\n{error.custom_help_msg}"
    print(msg)
    await ctx.send(msg)
    if error.send_cmd_help:
      await ctx.send_help(ctx.command)
  elif isinstance(error, commands.ConversionError):
    if error.args:
      await ctx.send(error.args[0])
    else:
      await ctx.send_help(ctx.command)
  elif isinstance(error, commands.UserInputError):
    await ctx.send_help(ctx.command)
  elif isinstance(error, commands.CommandInvokeError):
      exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
      exception_log += "".join(
          traceback.format_exception(type(error), error, error.__traceback__)
      )
      bot._last_exception = exception_log
      oneliner = "Error in command '{}' - {}: {}".format(
              ctx.command.qualified_name, type(error.original).__name__,
              str(error.original))
      await ctx.send(f'```py\n{oneliner}```')

bot.on_command_error = on_command_error

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
async def penis(ctx, user: discord.Member=None):
    """Detects user's penis length
    This is 100% accurate."""

    state = random.getstate()
    if user is None:
      user = ctx.author

    random.seed(user.id)
    dong = "8{}D".format("=" * random.randint(0, 30))

    random.setstate(state)
    msg = "{}'s size:\n{}\n".format(user.display_name, dong)

    await ctx.send(msg)

"""
!quest
  !quest list [class|search term|quest master|"party"|"solo"] [sort_by(recent|xp|party)]
  !quest info <quest_name>
  !quest accept <name> [party_member_mentions]
  !quest log [quest_name_or_number][.task_name_or_number] ["pending"] (is there a better word?)
  !quest new <options>
   <name>
   [option:value]
   [description]
   options:
    party=1 (or open)
    xp=0 (required if no xp in tasks)
    expires=2w (-1 for never)
    time=2w (-1 for never)
    repeats=0 (-1 for infinite)
    redoes=no
    progression=no
  !quest task add <quest#>[.task#] <value>
    <name>
    [desc]
    [part_list]
      [xp]-<part_desc>

  !quest task set <quest#.task#>[.part#] <value>
  !quest task delete <quest#.task#>[.part#]

  !quest set <option> <quest#> [value]
    if xp or repeats increase, must pay the difference
    can't change party of published quests

  !quest publish|post <quest#>

  !quest setreminder 1d <quest#> (admin use only)
  !quest notify [class|search term|quest master|"party"|"solo"] (turns on/off notifications for new quests that match search term)

  !quest claim <quest#>[.task#][.part#] [desc]
  !quest verify <message_id>

  !quest leaderboard [quest_name[.task_name]]
"""

def int_parser(default, minv=None, maxv=None):
  def int_parser_pred(s):
    mn=minv
    mx=maxv
    if s is None:
      return default
    try:
      v = int(s)
    except ValueError:
      raise commands.ArgumentParsingError(f'{s} cannot be converted to a whole number')
    if mn is None:
      mx = v
    if mx is None:
      mx = v
    if v < mn:
      raise commands.ArgumentParsingError(f'{v} is less than the minimum value {mn}')
    if v > mx:
      raise commands.ArgumentParsingError(f'{v} is greater than the maximum value {mx}')
    return v
  return int_parser_pred

SPAN_PATTERN = re.compile(r'(?P<amt>[0-9]+)(?P<span>[dw]?)')

def parse_delta(s):
  m = SPAN_PATTERN.match(s)
  n = int(xmatch.group('amt'))
  p = xmatch.group('span')
  if not p:
    p = 'd'
  if p not in 'dw'

def time_parser(default, minv, maxv):
  xmatch = SPAN_PATTERN.match(maxv)
  xn = int(xmatch.group('amt'))
  xs = xmatch.group('span')
  if xs 
  mmatch = SPAN_PATTERN.match(minv)
  mn = int(xmatch.group('amt'))
  ms = xmatch.group('span')  
  def time_parser_pred(s):
    if s is None:
      return default
    smatch = SPAN_PATTERN.match(minv)
    sn = xmatch.group('amt')
    ss = xmatch.group('span')
    now = datetime.now()
  pass

def bool_parser(default):
  def bool_parser_pred(s):
    if s is None:
      return default
    # from commands.converter
    lowered = s.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
        return False
    else:
      raise commands.ArgumentParsingError(f'cannot convert {s} to true/false')


QUEST_OPTION_PARSERS = {
  "xp": int_parser(0, 0),
  "party": int_parser(1, 0),
  "time": time_parser('2w', '1d', '8w'),
  "expires": time_parser('2w', '1d', '4w'),
  "progression": bool_parser(False),
  "repeats": int_parser(0, 0),
  "redoes": bool_parser(False)
}


def save_bot_settings():
  db['BOT_SETTINGS'] = deepcopy(bot_settings)

def save_quests():
  db['QUEST_SETTINGS'] = deepcopy(quest_settings)

@bot.group(name="set")
@commands.is_owner()
async def _set(ctx):
  """bot settings"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

@_set.group()
async def admin(ctx, role: discord.Role):
  """bot settings"""
  bot_settings['admin_role'] = role.id
  save_bot_settings()
  await ctx.send(f'admin role set to {role.name}')

def is_admin():
  def predicate(ctx):
    return bot_settings['admin_role'] in [r.id for r in ctx.message.author.roles]
  return commands.check(predicate)

def is_quest_master():
  def predicate(ctx):
    return quest_settings['quest_master_role'] in [r.id for r in ctx.message.author.roles]
  return commands.check(predicate)

def is_quest_master_or_admin():
  def predicate(ctx):
    return is_quest_master()(ctx) or is_admin()(ctx)
  return commands.check(predicate)

@bot.group()
async def quest(ctx):
  """quest commands"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

@quest.command(name="masterrole")
@is_admin()
async def master_role(ctx, role: discord.Role=None):
  """set the quest master role. leave blank to unset"""
  rid = role and role.id
  quest_settings['quest_master_role'] = rid
  save_quests()
  if rid is not None:
    await ctx.send(f'quest master role set to {role.name}')
  else:
    await ctx.send('quest master role has been unset')

@quest.command()
@is_quest_master_or_admin()
async def new(ctx, *, options:str):
  """start creating a new quest. options must be in the following format on separate lines:
  
  <name>
  [option_name=option_value]
  ...
  [description]

  available options are:
             xp - defaults to 0. bonus xp for completing the quest. 
          party - defaults to 1. party size required to start the quest. 
                  set to 0 for an open quest; a quest that anybody can
                  contribute to at any time.
           time - defaults to 2w. the time limit for parties to complete
                  the quest once started. range is 1d - 8w.
                  (admins can set this to 0 for no time limit)
        expires - defaults to 2w. the time your quest will stay on the
                  quest board. range is 1d - 4w (1 day - 4 weeks). 
                  (admins can set this to 0 for no expiration)
    progression - defaults to no. whether or not tasks are hidden to 
                  adventurers until they complete the previous task.
        repeats - defaults to 0. the number of times a quest can be 
                  taken before it is taken off the quest board. 
                  (admins can set this to -1 to allow infinite repeats)
         redoes - defaults to no. when a quest has repeats, this option 
                  specifies whether an adventurer is allowed to take the 
                  quest again.
  
  examples:
    !quest new Dog Bones
    xp=10
    I need more bones to create my army of bloodhounds.
    Get me 2s and I'll make it worth your while.
    Prize: 1 diamond

    !quest new Rockets Red Glare
    xp=50
    time=1w
    progression=yes
    party=3
    I need me some rockets to celebrate my freedom
  """
  options = options.strip()
  name, *options = [o.strip() for o in options.split('\n')]
  

  await ctx.send(f'name: {name}\noptions: {options}')


@quest.command()
async def list(ctx, search_term: str=None, sort_by: str=None):
  """lists all available quests. You can also narrow your search using a search term.

    search_term: can be one of the following:
             class - one of the available quest classes(tags). 
                     use .quest classes for a list.
      quest master - the @mention of the quest master/creator.
        party type - party, solo, or open
       search term - any other generic term to search for in the quest

    sort_by: a term to sort by when displaying the list. can be:
            recent - most recent quests first. this is the default.
               old - oldest quests first.
                xp - quests with highest xp reward first.
             party - quests with highest party size first.

  """
  pass

@quest.command()
async def info(ctx):
  '''Help 
   !quest info <questID> - Gives all all information currently availale about a quest 
  '''
  pass

@quest.command()
async def accept(ctx):
  '''Help 
    !quest accept <questID> [all @ party members] - Accepts a quest either by yourself or with the mentioned members 
  '''
  pass

@quest.command()
async def log(ctx):
  '''Help 
   !quest log [questID] [ .taskID]  - Gives information about a quest in progress including current completion percent/level
  '''
  pass

@quest.command(name="set")
async def quest_set(ctx):
  '''Help 
  !quest set <option> <questID> [value] - Edits a quest at a later point, e.g to add missed tags or increase xp reward
  '''
  pass

@quest.command()
async def claim(ctx):
  '''Help 
  !quest claim <questID> [ .TaskID] [decription] - Claims a quest / task is complete with description to await verification
  '''
  pass

@quest.command()
async def verify(ctx):
  '''Help 
   !quest verify <message_id> - Verifies claims (Questmaster only)
  '''
  pass

@quest.command()
async def leaderboard(ctx):
  '''Help 
   !quest leaderboard [quest_name[.task_name]] - Displays leaderboard of global levelor specified quest xp
  '''
  pass

@quest.command()
async def notify(ctx):
  '''Help 
    !quest notify [class|search term|quest master|"party"|"solo"] -  Notifys of quests posts matching specified parameters
  '''
  pass

@quest.group()
async def task(ctx):
  """hlel
  """
  pass

@task.command(name="add")
async def task_add(ctx):
  '''Help 
   !quest task add <questID> [ .TaskID] <options> - Creates a new numbered task within a stated quest
   '''
  pass

@task.command(name="set")
async def task_set(ctx):
  '''Help
 !quest task set <questID . TaskID>  - Edits a task at later point to e.g add/remove objectives or xp rewards
   '''
  pass

@task.command(name="delete")
async def task_delete(ctx):
  '''Help 
  !quest task delete <questID . TaskID> - Deletes the specified task
   '''
  pass


# this runs the web server
server.keep_alive()

bot.run(my_secret, reconnect=True) # <-- reconnects if it disconnects