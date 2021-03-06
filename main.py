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
from typing import List, Tuple, Union
import textwrap
from contextlib import redirect_stdout
import io
import asyncio
import aiohttp
import pytz
import re
import json

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True
intents.presences = True

PREFIX = '.'
bot = commands.Bot(command_prefix=PREFIX, description=description, intents=intents, owner_id=owner_id)

bot.prefix = PREFIX

ATTACHMENT_BASE_URL = "https://cdn.discordapp.com/attachments/"

def gen_attachment_url(channel_id, attachment_id, filename):
  return ATTACHMENT_BASE_URL + f"{channel_id}/{attachment_id}/{filename}"

##### setting up persistent data that isn't reliant on replit db size limit #####
DATA_FOLDER = 'data/'
# put your data names here followed by default values they should be. if those defaults aren't there, the bot will add them when it restarts. it only checks one level deep though.
DATA_FILES_DEFAULTS = {
  'custom_commands': {
    'triggers': {}
  },
}

bot.data = {}

# from Red
def _read_json(filename):
    with open(filename, encoding='utf-8', mode="r") as f:
        data = json.load(f)
    return data

def _save_json(filename, data):
    with open(filename, encoding='utf-8', mode="w") as f:
        json.dump(data, f, indent=4,sort_keys=True,
            separators=(',',' : '))
    return data

if not os.path.exists(DATA_FOLDER):
  os.mkdir(DATA_FOLDER)

for fn, defaults in DATA_FILES_DEFAULTS.items():
  if not os.path.exists(DATA_FOLDER + fn + '.json'):
    _save_json(DATA_FOLDER + fn + '.json', defaults)

def save_data(fn):
  if fn not in DATA_FILES_DEFAULTS:
    raise FileNotFoundError("that data file doesn't exist")
  data = bot.data[fn]
  _save_json(DATA_FOLDER + fn + '.json', data)

for fn in DATA_FILES_DEFAULTS:
  data = DATA_FILES_DEFAULTS[fn]
  from_json = _read_json(DATA_FOLDER + fn + '.json')
  # set defaults, override w/ the actual data
  data = {**data, **from_json}
  bot.data[fn] = data
  
##### data setup end. use save_data to save changes to bot.data #####


BOT_DEFAULT_SETTINGS = {'admin_role': None}

if 'BOT_SETTINGS' not in db.keys():
  db['BOT_SETTINGS'] = deepcopy(BOT_DEFAULT_SETTINGS)

bot_settings = deepcopy(db['BOT_SETTINGS'])

QUEST_DEFAULT_SETTINGS = {'quest_master_role': None}

if 'QUEST_SETTINGS' not in db.keys():
  db['QUEST_SETTINGS'] = deepcopy(QUEST_DEFAULT_SETTINGS)

quest_settings = deepcopy(db['QUEST_SETTINGS'])

if 'ONGOING_QUESTS' not in db.keys():
  db['ONGOING_QUESTS'] = {}

ongoing_quests = deepcopy(db['ONGOING_QUESTS'])

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
    try:
      msg = "`{user_input}` is not a valid value for `{command}`".format(
        user_input=error.user_input, command=error.cmd
      )
      if error.custom_help_msg:
        msg += f"\n{error.custom_help_msg}"
    except:
      msg = error.args[0]
    print(msg)
    await ctx.send(f'```py\n{msg}```')
    try:
      if error.send_cmd_help:
        await ctx.send_help(ctx.command)
    except:
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

@bot.listen()
async def on_error(event, *args):
  print('event: ---')
  print(event)
  print('args: ----')
  print(args)
  # if isinstance(error, commands.MissingRequiredArgument)
    # await aiohttp.get(f'https://BotRestarter.funkydevs.repl.co?callback={urllib.parse.quote_plus("https://FunkyBot.funkydevs.repl.co")}')
    # os.system('kill 1')
    

# from https://github.com/phenom4n4n/phen-cogs/blob/36306d29b86c9bf55b142e8bb680886d4fb2fea1/roleutils/reactroles.py#L99
def emoji_id(emoji):
  return emoji if isinstance(emoji, str) else str(emoji.id)

async def emoji_from_id(guild, emoji_id):
  return (await guild.fetch_emoji(int(emoji_id))) if len(emoji_id) > 2 else emoji_id

  
async def reaction_menu(ctx, msg, emojis_add_responses, emojis_rm_responses, from_members: list=[], timeout=30, update_task=None, update_task_poll_every=2, reset_timeout_if_respond=True):
  """turns a msg into a continuous reaction menu lasting timeout seconds.
  reactions should be in place already before calling this
  
  emojis_add_responses and emojis_rm_responses should be maps between the emoji_id and callables expecting callable(reaction, user). callables should return not None to stop the reaction menu.

  from_members should be a list of users to watch for or an empty list to watch for any reaction (besides the bot)

  an awaitable update/display task can be given which will run during the reaction menu with update_task_poll_every second sleeps between each run
  """
  
  def rcheck(emojis):
    def check_pred(reaction, user):
      return (
        (
          (not from_members) and bot.user.id != user.id or
          (from_members and user.id in [a.id for a in from_members])
        ) and
        reaction.message.id == msg.id and
        emoji_id(reaction.emoji) in emojis
      )
    return check_pred
  
  async def update():
    while True:
      await asyncio.sleep(update_task_poll_every)
      await update_task()

  def process(event, group):
    async def process_pred():
      reaction, user = await bot.wait_for(event, check=rcheck(group))
      eid = emoji_id(reaction.emoji)
      if eid in group:
        return group[eid](reaction, user)
    return process_pred


  tasks = [
    process('reaction_add', emojis_add_responses),
    process('reaction_remove', emojis_rm_responses)
  ]
  if update_task:
    tasks.append(update)

  async def menu():
    while True:
      timeout_task = bot.loop.create_task(asyncio.sleep(timeout))
      batch = [timeout_task, *[t() for t in tasks]]
      done, pending = await asyncio.wait(batch, return_when=asyncio.FIRST_COMPLETED)
      for p in pending:
        p.cancel()
      if timeout_task in done:
        raise asyncio.exceptions.TimeoutError
      try:
        dp = done.pop().result()
      except Exception as e:
        print(e)
      if dp is not None:
        return dp

  if reset_timeout_if_respond:
    return await menu()
  else:
    return await asyncio.wait_for(menu(), timeout)

async def wait_for_reaction_response(ctx, msg_or_msg_str, reactions, from_members=[], timeout=None):
  """wait for a single reaction to be clicked on a message. adds the reactions if not there. if msg_or_msg_str is a string, it sends the message. returns the emoji or None if they don't respond by timeout"""
  msg = msg_or_msg_str
  if msg_or_msg_str.content is None:
    msg = await ctx.send(msg_or_msg_str)
  
  for r in reactions:
    try:
      await msg.add_reaction(r)
    except:  # assumes it was just there already but could also be permissions
      pass

  response = {}
  def reaction_curry(r):
    def radd(_, __):
      response['r'] = r
      return r
    return radd
  adds = {r: reaction_curry(r) for r in reactions}

  opts = {}
  if timeout:
    opts = {'timeout': timeout}
  try:
    await reaction_menu(ctx, msg, adds, {}, from_members, **opts)
  except asyncio.TimeoutError:
    return None
  return response['r']

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

# example of using an argument/parameter instead:
@bot.command()
async def cool(ctx, member=None):
  """Says if a user is cool."""
  if member is None:
    member = ctx.message.author.display_name

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
      raise commands.ArgumentParsingError(f'{s} cannot be converted to a whole number', s)
    if mn is None:
      mn = v
    if mx is None:
      mx = v
    if v < mn:
      raise commands.ArgumentParsingError(f'{v} is less than the minimum value {mn}', v)
    if v > mx:
      raise commands.ArgumentParsingError(f'{v} is greater than the maximum value {mx}', v)
    return v
  return int_parser_pred

SPAN_PATTERN = re.compile(r'(?P<amt>[0-9]+)(?P<span>[dw])')

def parse_delta(s):
  if s == '0':
    return 0
  m = SPAN_PATTERN.match(s)
  if not m:
    raise commands.ArgumentParsingError(f'{s} is not a valid timespan format.', s)
  n = int(m.group('amt'))
  p = m.group('span')
  if p == 'w':
    n *= 7
  return n

def time_parser(default, minv, maxv):
  df = parse_delta(default)
  mn = parse_delta(minv)
  mx = parse_delta(maxv)
  def time_parser_pred(s):
    if s is None:
      return df
    days = parse_delta(s)
    if days < mn:
      raise commands.ArgumentParsingError(f'{s} is less than the minimum value {minv}', s)
    if days > mx:
      raise commands.ArgumentParsingError(f'{s} is greater than the minimum value {maxv}', s)
    return days
  return time_parser_pred

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
      raise commands.ArgumentParsingError(f'cannot convert {s} to true/false', s)
  return bool_parser_pred


QUEST_OPTION_PARSERS = {
  "xp": int_parser(0),
  "party": int_parser(1, 0),
  "time": time_parser('2w', '1d', '8w'),
  "expires": time_parser('2w', '1d', '4w'),
  "progression": bool_parser(False),
  "repeats": int_parser(0, 0),
  "redoes": bool_parser(False),
  "retries": int_parser(0, 0)
} 
ADMIN_QUEST_OPTION_PARSERS = {
  "xp": int_parser(0),
  "party": int_parser(1, 0),
  "time": time_parser('2w', '0d', '8w'),
  "expires": time_parser('2w', '0d', '4w'),
  "progression": bool_parser(False),
  "repeats": int_parser(0, -1),
  "redoes": bool_parser(False),
  "retries": int_parser(0, -1)
}
QUEST_OPTION_DEFAULTS = {
  "xp": 0,
  "party": 1,
  "time": 14,
  "expires": 14,
  "progression": False,
  "repeats": 0,
  "redoes": False,
  "retries": 0,
}

def save_bot_settings():
  db['BOT_SETTINGS'] = deepcopy(bot_settings)

def save_quests():
  db['QUEST_SETTINGS'] = deepcopy(quest_settings)
  db['ONGOING_QUESTS'] = deepcopy(ongoing_quests)

def check_is_admin(member):
  return bot_settings['admin_role'] in [r.id for r in member.roles] or member.id == owner_id
bot.check_is_admin = check_is_admin

def check_is_quest_master(member):
  return quest_settings['quest_master_role'] in [r.id for r in member.roles]
bot.check_is_quest_master = check_is_quest_master

def is_admin():
  def _is_admin(ctx):
    return check_is_admin(ctx.message.author)
  return commands.check(_is_admin)

def is_quest_master():
  def predicate(ctx):
    return check_is_quest_master(ctx.message.author)
  return commands.check(predicate)

def is_quest_master_or_admin():
  def predicate(ctx):
    return is_quest_master()(ctx) or is_admin()(ctx)
  return commands.check(predicate)

# from https://github.com/phenom4n4n/phen-cogs/blob/36306d29b86c9bf55b142e8bb680886d4fb2fea1/roleutils/converters.py#L112
class RealEmojiConverter(commands.EmojiConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> Union[discord.Emoji, str]:
        try:
            emoji = await super().convert(ctx, argument)
        except commands.BadArgument:
            try:
                await ctx.message.add_reaction(argument)
            except discord.HTTPException:
                raise commands.EmojiNotFound(argument)
            else:
                emoji = argument
        return emoji

def questPartConverterFactory(max_depth=3):
  class QuestPartConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
      types = ['quest', 'task', 'objective']
      if argument.count('.') >= max_depth:
        raise commands.BadArgument(f'can only select up to {types[max_depth-1]}')
      try:
        parse_quest_id(argument)
      except:
        raise commands.BadArgument(f'{argument} is not the right format')
      try:
        tp = types[argument.count('.')]
      except:
        raise commands.BadArgument(f'{argument} is not the right format')
      try:
        q = resolve_quest_id(argument)
      except:
        raise commands.BadArgument(f'{argument} not found.')
      return (q, tp)
  return QuestPartConverter

TASK_BLURB_PATTERN = r"(<name>.*)(\nxp=)?"

class TaskConverter(commands.Converter):
  async def convert(self, ctx: commands.Context, task_blurb: str):
    task = {
      'objectives': [],
      'desc': '',
      'xp': 0,
    }
    try:
      title, rest = task_blurb.split('\n', 1)
    except:
      task['name'] = task_blurb.strip()
      return task
    task['name'] = title

    title = title.strip()
    rest = rest.strip()

    if rest.startswith('xp='):
      rest = rest.split('xp=')[1]
      xp, *rest = rest.split('\n', 1)
      xp = int(xp.strip())
      if xp < 0:
        raise commands.BadArgument(f'xp cannot be negative')
      task['xp'] = xp
      if not rest:
        return task
      rest = rest[0]

    pn = 0
    desc = ''
    desc_done=False
    objs = []
    obj = {}
    while True:
      last = False
      try:
        n = rest.index('\n', pn)
      except:
        line = rest[pn:]
        last = True
      else:
        line = rest[pn:n].strip()
      line = line.strip()
      if line.startswith('-'):
        if not desc_done:
          desc = rest[:pn].strip()
          desc_done = True
        else:
          obj['desc'] = rest[:pn].strip()
          objs.append(obj)
        obj = {'xp': 0}
        rest = rest[pn:].strip()
        rest = rest[1:]
        pn = 0
        if last:
          obj['desc'] = rest.strip()
          objs.append(obj)
          break
        continue
      if '-' in line:
        xp, objst = line.split('-',1)
        no = {}
        try:
          no['xp'] = int(xp)
        except:
          pass
        else:
          if not desc_done:
            desc = rest[:pn].strip()
            desc_done = True
          else:
            obj['desc'] = rest[:pn].strip()
            objs.append(obj)
          obj = no
          rest = rest[pn:].strip()
          rest = rest[line.index('-')+1:]
          pn = 0
          if last:
            obj['desc'] = rest.strip()
            objs.append(obj)
            break
          continue
      pn = n+1
      if last:
        obj['desc'] = rest.strip()
        objs.append(obj)
        break

    task['desc'] = desc
    task['objectives'] = objs
    return task


@bot.command(name="error")
# @is_admin()
async def _error(ctx):
  """display the bot's last exception"""
  await ctx.reply(f'```py\n{bot._last_exception}```')


@bot.group(name="set")
@is_admin()
async def _set(ctx):
  """bot settings"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

@_set.command()
@commands.is_owner()
async def admin(ctx, role: discord.Role):
  """bot settings"""
  bot_settings['admin_role'] = role.id
  save_bot_settings()
  await ctx.reply(f'admin role set to {role.name}')

@bot.group()
@is_admin()
async def role(ctx):
  """admin role commands"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

async def give_take_role_from_everyone(ctx, role, give=True, reason=None, update_msg_fmt=""):
  lmem = len(ctx.guild.members)
  msg = await ctx.reply(update_msg_fmt.format(0))
  
  progress = {'n': 0}

  async def do_roles():
    for m in ctx.guild.members[progress['n']:]:
      if give:
        await m.add_roles(role, reason=reason)
      else:
        await m.remove_roles(role, reason=reason)
      progress['n'] += 1
  
  while progress['n'] < lmem:
    try:
      await asyncio.wait_for(do_roles(), 5)
    except asyncio.exceptions.TimeoutError:
      await msg.edit(content=update_msg_fmt.format(progress['n']))
    else:
      await msg.edit(content=update_msg_fmt.format(progress['n']) + '. Done!')
      break

@role.command()
async def giveall(ctx, role: discord.Role, *, reason):
  """give a role to everyone. A reason must be specified for the audit log"""
  if not reason:
    await ctx.reply('make sure to give a reason for adding this role to everyone')

  lmem = len(ctx.guild.members)
  fmt = (f"This is gonna take awhile.. {role} added to "
         "{}" 
         f"/{lmem} members")
  await give_take_role_from_everyone(ctx, role, reason=reason, update_msg_fmt=fmt)

@role.command()
async def takeall(ctx, role: discord.Role, *, reason):
  """take away a role from everyone. A reason must be specified for the audit log"""
  if not reason:
    await ctx.reply('make sure to give a reason for taking this role from everyone')

  lmem = len(ctx.guild.members)
  fmt = (f"This is gonna take awhile.. {role} removed from "
         "{}" 
         f"/{lmem} members")
  await give_take_role_from_everyone(ctx, role, give=False, reason=reason, update_msg_fmt=fmt)

quest_tag_list_by_emoji={}
def generate_tag_emoji_map():
  global quest_tag_list_by_emoji
  quest_tag_list_by_emoji = {
    v:k for k,v in quest_settings['tags'].items()
  }

def setup_quests():
  defaults = {
    'tags': {},
    'quests': {},
    'claims': {},
    'quest_counter': 1,
    'ongoing_quest_counter': 1
  }
  changed = False
  for k, v in defaults.items():
    if k not in quest_settings:
      changed = True
      quest_settings[k] = deepcopy(v)
  if changed:
    save_quests()
  generate_tag_emoji_map()
  
setup_quests()


async def gen_tag_list(ctx):
  msg = '__**Quest Tags**__:\n'
  split_at=3
  i=0
  for tag, eid in quest_settings['tags'].items():
    i+=1
    s = f'{await eid_convert(ctx, eid)} **{tag}**  '
    if not i%split_at:
      s += '\n'
    msg += s
  return msg

async def list_tags(ctx):
  msg = await gen_tag_list(ctx)
  return await ctx.reply(msg)

async def emoji_from_tag(ctx, tag):
  return await eid_convert(ctx, quest_settings['tags'][tag])

async def eid_convert(ctx, eid):
  try:
    eid = await emoji_from_id(ctx.guild, eid)
  except:
    eid = f':{eid}:'
  return eid


@_set.command()
@is_admin()
async def questtag(ctx, tag_name: str=None, emoji: RealEmojiConverter=None):
  """add/removes tags used in tagging quests. leave tag_name empty to list the tags. leave emoji empty to delete the tag"""
  # revisit what happens to quests with tags that get removed?
  # probably best to just save em as text and nvmd doing anything if they get removed
  
  if tag_name is None:
    await list_tags(ctx)
    return

  if emoji:
    old = quest_settings['tags'].get(tag_name)
    quest_settings['tags'][tag_name] = emoji_id(emoji)
    quest_settings['tags'] = {  # sort
      i: quest_settings['tags'][i] for i in sorted(quest_settings['tags'].keys())
    }
    save_quests()
    if old:
      old = await eid_convert(ctx, old)
      await ctx.reply(f'The emoji for the quest tag {old} **{tag_name}** was changed to {emoji}')
    else:
      await ctx.reply(f'{emoji} **{tag_name}** was added as a quest tag')
  else:  # delete
    if not quest_settings['tags'][tag_name]:
      await ctx.reply(f'**{tag_name}** is already not a quest tag')
    else:
      eid = quest_settings['tags'][tag_name]
      emoji = await eid_convert(ctx, eid)
      del quest_settings['tags'][tag_name]
      save_quests()
      await ctx.reply(f'quest tag {emoji} **{tag_name}** was deleted')


def setup_hammertime():
  if 'hammertime' not in bot_settings:
    bot_settings['hammertime'] = {
      'roles': {},
      'users': {}
    }
    save_bot_settings()

NOT_A_TIMEZONE_MSG = "is not an available time zone. Use a timezone available at https://hammertime.djdavid98.art/ or if one of those don\'t work, use one from <https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568>"

@_set.command()
async def hammertimerole(ctx, role: discord.Role=None, timezone:str=None):
  """add or remove a discord role as a role to be used with the hammertime command. 
  
  Leave timezone blank to remove the role from hammertime.
  
  Use the command by itself to list the roles currently added.
  """
  setup_hammertime()
  
  if role is None:
    roles = '  '.join(sorted([ctx.guild.get_role(int(rid)).name for rid in bot_settings['hammertime']['roles']]))
    return await ctx.reply(f'Roles used with `{bot.prefix}hammertime`:\n**{roles}**')
  
  if timezone is None:
    if str(role.id) not in bot_settings['hammertime']['roles']:
      return await ctx.reply(f'**{role}** is already not being used with hammertime')
    del bot_settings['hammertime']['roles'][str(role.id)]
    save_bot_settings()
    return await ctx.reply(f'**{role}** removed from hammertime.')
  else:
    if timezone not in pytz.all_timezones:
      return await ctx.reply(f'{timezone} {NOT_A_TIMEZONE_MSG}')
    bot_settings['hammertime']['roles'][str(role.id)] = timezone
    save_bot_settings()
    return await ctx.reply(f'the **{role}** role has been added to hammertime. People with this role will now be treated as being in that timezone when using `{bot.prefix}hammertime`')


def parse_quest_options(tokens, parsers):
  options = {}
  last_option_line_n = 0
  for c, op in enumerate(tokens):
    last_option_line_n += 1
    if not op.strip():
      continue
    try:
      key, val = [i.strip() for i in op.split('=')]
      parser = parsers[key]
    except:
      break
    else:
      parsed = parser(val)
    if not QUEST_OPTION_DEFAULTS[key] == parsed:
      options[key] = parser(val)  
  
  return (options, last_option_line_n)


def parse_quest_id(s):
  """fails if it's not in 1.2.3 format"""
  ns = s.split('.')
  ins = [int(i) for i in ns]
  return [ns[0], *ins[1:]]
    
def resolve_quest_id(s):
  ids = parse_quest_id(s)
  ret = quest_settings
  keys = ['quests', 'tasks', 'objectives']
  prev = None
  try:
    for i, key in zip(ids, keys):
      if key != 'quests':
        i -= 1
      prev = ret
      ret = ret[key][i]
      if key == 'objectives':
        ret = (ret, prev)
  except:
    tps = ['quest', 'task', 'objective']
    tp = tps[s.count('.')][:-1]

    raise KeyError(f"can't find {tp} {s}")
  return ret

@bot.group()
async def quest(ctx):
  """quest commands"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

@quest.command(name="masterrole")
@is_admin()
async def master_role(ctx, role: discord.Role=None):
  """Set the Quest Master Role. Leave blank to unset"""
  rid = role and role.id
  quest_settings['quest_master_role'] = rid
  save_quests()
  if rid is not None:
    await ctx.send(f'quest master role set to {role.name}')
  else:
    await ctx.send('quest master role has been unset')

async def _gen_desc(quest, author):
  s = quest['desc']
  if quest['tags']:
    el = ''.join([str(await emoji_from_id(author.guild, quest_settings['tags'][t])) for t in quest['tags'] if t in quest_settings['tags']])
    s = f'{s}\n\n{el}'
  return s

def get_quest_author(quest, guild):
  return guild.get_member(int(quest['owner']))

def get_player(author_id):
  aid = str(author_id)
  player = quest_settings['players'].get(aid, {
    'id': aid,
    'xp': 0,
    'active': {},
    'completed': {}
  })
  return player

def get_quest_total_task_xp(quest):
  return sum([
      t.get('xp',0) + sum(o['xp'] for o in t.get('objectives',[]))
      for t in quest['tasks']
    ])


async def new_quest_embed(quest, guild, task=None):
  ongoing = 'qid' in quest
  if ongoing:
    ongoing = quest
    quest = quest_settings['quest'][quest['qid']]
  name = quest['name']
  author = get_quest_author(quest, guild)
  desc = await _gen_desc(quest, author)

  author_type = 'quest master'
  if check_is_admin(author):
    author_type = 'Admin'

  qn = quest.get('id', '_')
  embed = discord.Embed(
    title=f'{qn}. {name}',
    description=desc,
    color=author.color
  )

  def expire_fmt(v, f):
    if not v:
      return ''
    
    now = datetime.now()
    nowi = int(datetime.now().timestamp())
    expires = datetime.fromtimestamp(int(quest['posted']) or nowi) + timedelta(days=v)
    left = expires - now

    span = 'day'
    amt = left.days
    if amt >= 7*2:
      amt//=7
      span = 'week'
    elif amt <= 1:
      amt=left.total_seconds()/60
      span = 'minute'
      if amt > 59:
        amt/=60  # if hours or minutes then regular rounding 
        span = 'hour'
    
    if amt > 1:
      span += 's'
    
    return f'quest expires in __{round(amt)} {span}__'
  
  def time_fmt(v, f):
    if not v:
      return ""
    s = f'time limit: **{v if v%7 else v//7} {"day" if v%7 else "week"}{"" if v in (1,7) else "s"}**'
    r = f.get('retries', 0)
    if r:
      s += f" ({'infinite' if r<0 else r} retr{'y' if r==1 else 'ies'})"
    return s
  
  def xp_fmt(v, f):
    task_xp = get_quest_total_task_xp(f)
    
    bonus = max(0, v)
    total_xp = bonus + task_xp
    s = f'reward: **{total_xp} xp**'
    if total_xp > bonus:
      s = 'total ' + s
    if v < 0:
      s = f'`cost: {v} xp`\n' + s
    return s

  option_fmt = {
    'party': lambda v,f: '***open** quest*' if v<1 else '*solo quest*' if v<2 else f'*party size: **{v}***',
    'time': time_fmt,
    'expires': expire_fmt,
    'tasks': lambda v,f: f'0/{len(v)} tasks' if len(v) else '',
    'xp': xp_fmt,
  }

  ext_opt = {
    'party': QUEST_OPTION_DEFAULTS['party'],
    'expires': QUEST_OPTION_DEFAULTS['expires'],
    **quest['options'], 
    'tasks': quest['tasks']
  }

  embed.add_field(
    name='Details',
    value='\n'.join(filter(None, [
      v(ext_opt[k], ext_opt) for k, v in option_fmt.items() if k in ext_opt
    ]))
  )
  
  async def gen_footer():
    ft = f'{author.display_name} ??? {author_type}'
    # if quest['tags']:
    #   el = ''.join([str(await emoji_from_id(ctx, quest_settings['tags'][t])) for t in quest['tags'] if t in quest_settings['tags']])
    #   ft += f'  |  {el}'
    return ft

  footer_txt = await gen_footer()

  embed.set_footer(
    text=footer_txt
  )

  return embed

def quest_is_available(quest):
  if not quest['posted']:
    return False
  if quest['posted'] is True:
    return True
  days = int(quest['options'].get('expires',0))
  now = datetime.now()
  expiration = datetime.fromtimestamp(int(quest['posted'])) + timedelta(days=days)
  if now > expiration:
    return False
  return True

def get_quest_xp(quest):
  task_xp = sum([
      t.get('xp',0) + sum(o['xp'] for o in t.get('objectives',[]))
      for t in quest['tasks']
  ])
  qxp = max(quest['options'].get('xp', 0), 0)
  return task_xp + qxp
  
@quest.command()
@is_quest_master_or_admin()
async def new(ctx, *, options:str):
  """Start creating a new quest. 
  options must be in the following format on separate lines:
  
  <name>
  [option_name=option_value]
  ...
  [description]

  available options are:
             xp - defaults to 0. bonus xp for completing the quest. 
                  set negative to add a cost for starting the quest.
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
                  quest again after completing it.
        retries - defaults to 0. the number of retries a party will 
                  have after exceeding the quest's time limit before 
                  the quest returns to the quest board.
                  (admins can set this to -1 for infinite retries)
  
  examples:
    .quest new Dog Bones
    xp=10
    I need more bones to create my army of bloodhounds.
    Get me 2s and I'll make it worth your while.
    Prize: 1 diamond

    .quest new Rockets Red Glare
    xp=50
    time=1w
    progression=yes
    party=3
    I need me some rockets to celebrate my freedom
  """
  # TODO: disallow certain option combinations, .. if needed
  options = options.strip()
  ooptions = options
  name, *options = [o.strip() for o in options.split('\n')]

  parsers = QUEST_OPTION_PARSERS
  if check_is_admin(ctx.message.author):
    parsers = ADMIN_QUEST_OPTION_PARSERS

  opt_dict, last_line = parse_quest_options(options, parsers)
  desc = ooptions.split("\n", last_line)[-1]
  quest = {
    'name': name,
    'desc': desc,
    'options': opt_dict,
    'tags': {},
    'posted': False,  # None is hidden, datetime is posted time
    'tasks': [],
    'owner': str(ctx.author.id),
    'playing': {}, #  uid: oqid
    'played': {},
    'taken': 0  # how many times or if open, how many players
  }

  author = ctx.author

  embed = await new_quest_embed(quest, ctx.guild)

  msg = await ctx.reply(f"\**Review your quest before creating it as creating it uses up a quest number.**\n\n"
  f"Click on tag(s) you'd like to add to your quest by clicking on the corresponding reactions (You can see the list of tags and their names with `{bot.prefix}quest listtags`).\n"
  f"Once the tags are set, hit the ??? to create the quest or ??? to cancel.\n\n"
  f"Once created, you can still change settings and add tasks before you post your quest by using the `{bot.prefix}quest set` and `{bot.prefix}quest task` commands.\n"
  f"Finally, post your quest with `{bot.prefix}quest post`."
    ,embed=embed)

  curry_quest_stuff={
    'tags': set(quest['tags']),
    'create': None,
    'emojis': []
  }
  
  def create(reaction, user):
    curry_quest_stuff['create'] = True
    return True
  
  def cancel(reaction, user):
    curry_quest_stuff['create'] = False
    return False
  
  def add_tag(tag):
    def add_tag_pred(reaction, user):
      quest['tags'][tag] = True
      quest['tags'] = {i: quest['tags'][i] for i in sorted(quest['tags'].keys())}
    return add_tag_pred
  
  def rm_tag(tag):
    def rm_tag_pred(reaction, user):
      if tag in quest['tags']:
        del quest['tags'][tag]
    return rm_tag_pred
  
  responses = {
    '???': create,
    '???': cancel,
  }
  rm_responses = {}
  for t, eid in quest_settings['tags'].items():
    try:
      em = await emoji_from_id(ctx.guild, eid)
    except Exception as e:
      print(e)
    else:
      responses[eid]    = add_tag(t)
      rm_responses[eid] = rm_tag(t)
      curry_quest_stuff['emojis'].append(em)
  
  curry_quest_stuff['emojis'].append('???')
  curry_quest_stuff['emojis'].append('???')

  async def update_embed():
    while curry_quest_stuff['emojis']:
      await msg.add_reaction(curry_quest_stuff['emojis'][0])
      curry_quest_stuff['emojis'].pop(0)
    
    if set(quest['tags']) != curry_quest_stuff['tags']:
      embed.description = await _gen_desc(quest, author)
      # embed.set_footer(text=await gen_footer())
      curry_quest_stuff['tags'] = set(quest['tags'])
      await msg.edit(embed=embed)
  
  try:
    await reaction_menu(
      ctx, msg, 
      responses, 
      rm_responses, 
      from_members=[author], 
      timeout=60*3,
      update_task=update_embed, 
      update_task_poll_every=1,
      reset_timeout_if_respond=True,
    )
  except asyncio.exceptions.TimeoutError:
    pass
  
  if curry_quest_stuff['create'] is None:
    return await msg.reply(f"took too long to respond. The **{name}** quest wasn't created.")
  
  if curry_quest_stuff['create'] is False:
    return await msg.reply(f"**{name}** quest creation canceled.")
  
  qn = quest_settings['quest_counter']
  quest_settings['quest_counter'] += 1
  quest_settings['quests'][str(qn)] = quest
  quest['id'] = qn
  save_quests()

  s = (
    f"You've created quest **{qn}**, the **{name}** quest!\n\n"
  
    f"You can adjust it using the `{bot.prefix}quest set` commands or add tasks using `{bot.prefix}quest tast add {qn}`.\nOnce you're happy with your quest, post it for all adventurers to see with `{bot.prefix}quest post {qn}`!")
  if opt_dict.get('xp', 0) == 0:
    s += f"\n\nNOTE: No xp bonus is given for completing this quest. Make sure to add xp in your quest's task objectives before posting it."
  elif opt_dict['xp'] < 0:
    s += f"\n\nNOTE: This quest costs xp for adventurers to take. Make sure your adventurers gain xp by the end of the quest by adding xp to your quest's task objectives."

  await ctx.send(s)
    

@quest.command()
async def listtags(ctx):
  """Lists available tags for quests. Think one should be added? Ask an admin to add it!"""
  await list_tags(ctx)

@quest.command(name="list")
async def q_list(ctx):
  """Lists all available quests.
  """
  # just ignoring all the search stuff for now
  # async def list(ctx, search_term: str=None, sort_by: str=None):
  """Lists all available quests. 
  You can also narrow your search using a search term.

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
  quests = ''
  for i, q in quest_settings['quests'].items():
    if not quest_is_available(q):
      continue
    quests += f"**{i}**. __**{q['name']}**__\n\u200c \u200c \u200c \u200c "
    pn = q['options'].get('party', 1) 
    if pn == 0:
      quests += '***open***'
    elif pn == 1:
      quests += '*solo*'
    else:
      quests += '????????????? ' + str(q['options']['party'])
    quests += f" | {get_quest_xp(q)} xp"
    if q['tags']:
      quests += " | " + ''.join([str(await emoji_from_tag(ctx, t)) for t in q['tags']])
    quests += '\n'

  embed = discord.Embed(
    title=f'FunkyCraft Quest Board',
    description=quests
  )
  await ctx.reply(embed=embed)
  # embed.add_field(
  #   name='Details',
  #   value='\n'.join(filter(None, [
  #     v(ext_opt[k], ext_opt) for k, v in option_fmt.items() if k in ext_opt
  #   ]))
  # )

@quest.command() 
async def info(ctx, quest_id: questPartConverterFactory(3)):
  """Shows info about a quest listed in .quest list. 
  You can also use this command to check the progress of quests you've accepted.

  quest_id is the quest number. It can be made more specific by adding task and objective numbers separated by periods.
 
  Examples:
    .quest info 2      <-- quest 2
    .quest info 5.2.3  <-- quest 5, task 2, objective 3
  """
  quest, item_type = quest_id
  if item_type == 'quest':
    embed = await new_quest_embed(quest, ctx.guild)
  elif item_type == 'task':
    embed = gen_task_embed(quest, ctx.guild)
  else:
    embed = gen_obj_embed(quest, ctx.guild)

  await ctx.reply(embed=embed)


@quest.command(aliases=['publish'])
@is_quest_master_or_admin()
async def post(ctx, quest_number: questPartConverterFactory(1)):
  quest, _ = quest_number
  if int(quest['owner']) != ctx.message.author.id:
    return await ctx.reply("You don't own this quest!")
  if quest['posted']:
    embed = await ctx.reply(embed=await new_quest_embed(quest, ctx.guild))
    msg = await ctx.reply("You've already posted this quest! Take it down? You can always post it again later.")
    resp = await wait_for_reaction_response(
      ctx, msg, 
      ['???', '???'], from_members=[ctx.message.author],
      timeout=30
    )
    if resp is None:
      return await ctx.send("took too long to react. try again later")
    if resp != '???':
      await msg.edit(content='Ok. Keeping quest published.')
      return
    quest['posted'] = False
    save_quests()
    await embed.delete()
    await msg.edit(content=f"Quest **{quest['id']}** taken down.")
    return 
  task_xp = get_quest_total_task_xp(quest)
  if quest['options']['xp'] + task_xp <= 0:
    return await ctx.reply(f"Completing this quest gives adventurers {quest['options']['xp'] + task_xp} xp. They need to at least receive some xp for completing quests.")
  posted = True
  # add xp transaction here later
  days_till_expires = quest['options'].get('expires', 0)
  if days_till_expires != 0:
    posted = int(datetime.now().timestamp())

  quest['posted'] = posted
  save_quests()
  await ctx.reply(f"quest {quest['id']} has been posted! ppl can now see it with `{bot.prefix}quest list`")


@quest.command()
async def accept(ctx, quest_number: questPartConverterFactory(1), * party_members: discord.Member):
  """Accept a Quest by yourself or with Party Members!

  party members must hm?
  
  Example:
    .quest accept 2 @.Power @Deno
    .quest accept 3
  """
  # TODO: don't forget xp costs
  quest, _ = quest_number
  if not quest_is_available(quest):
    return await ctx.reply('That quest is not available to be taken.')
  
  if quest['options']['party'] == 0:
    return await ctx.reply("That quest is an open quest, you don't need to accept it, just start claiming things from it!")
  
  party_members = [set([ctx.message.author, *party_members])]

  if quest['options']['party'] != len(party_members):
    if quest['options']['party'] == 1:
      return await ctx.reply('That quest is a solo quest') 
    return await ctx.reply(f"That quest requires a party of {quest['options']['party']}.")

  cant_players = set()
  for p in party_members:
    if p.id in quest['playing']:
      cant_players.add(p)
    if quest['options'].get('redoes', QUEST_OPTION_DEFAULTS['redoes']) is False:
      if p.id in quest['played']:
        cant_players.add(p)

  if cant_players:
    return await ctx.reply(f"This party can't take this quest. These members are or have already taken this quest: {', '.join(p.mention for p in cant_players)}")
  

  # ask to accept
  embed = await new_quest_embed(quest, ctx.guild)
  ms = f"accept this quest?"

  if len(party_members) > 1:
    ms = f"{ctx.message.author.mention} wants to do this quest with you {' '.join(m.mention for m in party_members)}. Do you all accept?"
  msg = await ctx.reply(ms, embed=embed)

  curry_quest_stuff = {'party': {}, 'denied': False}

  def agree(reaction, user):
    curry_quest_stuff['party'][user.id] = user
    if len(curry_quest_stuff['party']) == len(party_members):
      return True
  
  def cancel(reaction, user):
    curry_quest_stuff['denied'] = user
    return False
  
  def rmagree(reaction, user):
    del curry_quest_stuff['party'][user.id]
  
  responses = {'???': agree, '???': cancel}
  rmreponses = {'???': rmagree}
  await msg.add_reaction('???')
  await msg.add_reaction('???')
  try:
    await reaction_menu(
      ctx, msg, responses, rmreponses, from_members=party_members, timeout=60*5
    )
  except asyncio.exceptions.TimeoutError:
    slowppl = [m for m in party_members if m.id not in curry_quest_stuff['party']]
    return await msg.reply(f"{' '.join([m.mention for m in slowppl])} didn't respond in time. Try again.")
  if curry_quest_stuff['denied']:
    if len(party_members) > 1:
      return await msg.reply(f"{curry_quest_stuff['denied'].mention} chose not to accept the quest. All party members must accept the quest to start one.")
    else:
      return await msg.edit('Canceled', embed=None)
  
  oqc = quest_settings['ongoing_quest_counter']
  quest_settings['ongoing_quest_counter'] += 1
  party_quest = {
    'id': oqc,
    'qid': quest['id'],
    'party': {str(m.id): 0 for m in party_members},
    'tasks': {},
    # where should claim and participation go. I guess in the tasks and stuff
    # '',
  }
  plos = [get_player(m) for m in party_members]
  for p in plos:
    quest['playing'][p['id']] = oqc
    p['active'][quest['id']] = oqc
    quest_settings['players'][p['id']] = p
  ongoing_quests[oqc] = party_quest
  save_quests()
  # TODO: add a poll loop to check for timed out quests and notify parties
  pass

@quest.command(name="set")
@is_quest_master_or_admin()
async def quest_set(ctx, quest_number: questPartConverterFactory(1), option, *, value):
  """Change options on your quests before you post them.

  Some options can still be changed after publishing but be considerate of Adventurers that may be taking the Quest at that time.

  tags is a valid option. When setting tags with this command, specify all tags you want to use by tag name (not emoji) separated by commas

  use the .quest task commands to edit tasks
  """
  quest, _ = quest_number
  author = ctx.message.author
  admin = check_is_admin(author)
  not_owner = quest['owner'] != str(author.id)
  ovalue = value

  if not_owner and not admin:
    return await ctx.reply('You are not the quest master that created this quest')

  option = option.lower()

  if option == 'tags':
    tags = [t.strip() for t in value.split(',')]
    not_tags = set(tags) - set(quest_settings['tags'])
    if not_tags:
      s = await gen_tag_list(ctx)
      return await ctx.reply(
        f'{", ".join(not_tags)} ' + 
        'are not valid tags' if len(not_tags)>1 else 'is not a valid tag' +
        f'. Choose from the following (make sure you use tag names, not emojis):\n\n{s}')
    else:
      value = {t: True for t in sorted(tags)}
      target = quest
  elif option in ('title', 'name'):
    option = 'name'
    target = quest
  elif option in ('desc', 'description'):
    option = 'desc'
    target = quest
  else:
    parsers = QUEST_OPTION_PARSERS
    if check_is_admin(ctx.message.author):
      parsers = ADMIN_QUEST_OPTION_PARSERS
    try:
      value = parsers[option](value)
    except Exception as e:
      return await ctx.reply(f'{ovalue} is not a valid option for {option}!')
    if option == 'party' and quest['posted']:
      if 0 in (value, quest['options'].get('party', QUEST_OPTION_DEFAULTS['party'])):
        return await ctx.reply("cannot change between open and non-open quest types once a quest is posted")

    target = quest['options']
  
  # you sure?
  also = ''
  if not_owner and admin:
    also = '\n' + ctx.guild.get_member(int(quest['owner'])).mention
    msg = await ctx.reply('You are not the creator of this quest, are you sure you want to change these options?')
    curry_quest_stuff = {'agree': False}

    def create(reaction, user):
      curry_quest_stuff['agree'] = True
      return True
    
    def cancel(reaction, user):
      curry_quest_stuff['agree'] = False
      return False
    
    responses = {'???': create, '???': cancel}
    await msg.add_reaction('???')
    await msg.add_reaction('???')
    try:
      await reaction_menu(
        ctx, msg, responses, {}, from_members=[author]
      )
    except asyncio.exceptions.TimeoutError:
      pass
    if not curry_quest_stuff['agree']:
      return await ctx.send('change canceled')

  if str(target.get(option, QUEST_OPTION_DEFAULTS.get(option))) == str(value):
    return await ctx.reply(f'{option} is already set to {ovalue}')
  
  # if already posted
  if quest['posted']:
    msg = await ctx.reply("are you sure you want to alter this already posted quest?")
    resp = await wait_for_reaction_response(
      ctx, msg, ['???', '???'], 
      from_members=[ctx.message.author],
      timeout=20
    )
    if resp is None:
      return await msg.reply("Took too long to react. Try again later")
    if resp != '???':
      await msg.edit(content="Canceled.")
      return
    # alter posted time
    if option == 'expires':
      if int(value) == 0:
        quest['posted'] = True
      else:
        quest['posted'] = int(datetime.now().timestamp())

  if value == QUEST_OPTION_DEFAULTS.get(option, None):
    del target[option]
  else:
    target[option] = value
  
  save_quests()

  disp_val = f'**{ovalue}**'
  if option == 'desc':
    disp_val = ovalue

  await ctx.reply(f"**{quest['id']}**. **{quest['name']}**: **{option}** set to {disp_val}" + also)
  
PARTICIPANT_PATTERN = re.compile(r"\s*(?:<@!?(?P<aid>\d+)>\s*)")

@quest.command()
async def claim(ctx, quest_id: questPartConverterFactory(3), *, participants_and_description: str=None):
  """Claim a Quest/Task/Objective with a description to await Verification!

  Example:
    .quest claim 4.3 The Diamonds are in the Mailbox!
    .quest claim 1.2.4 <picture of music discs>
    .quest claim 2.1.3 @Green @Susan We left a little extra in your barrels
  """
  # split last arg into members (ids) and description
  li = 0
  participants = []
  for m in PARTICIPANT_PATTERN.finditer(participants_and_description):
    participants.append(m.group('aid'))
    li = m.span()[-1]
  description = participants_and_description[li:]
  description = description.strip() or None

  item, item_type = quest_id
  quest = item
  task = None
  objective = None
  tid = None
  idstr = ''
  what = ''
  if item_type == "objective":
    objective, task = item
    quest = quest_settings['quests'][task['qid']]
    tid = quest['tasks'].index(task) + 1
    oid = task['objectives'].index(objective) + 1
    idstr = f'{quest["id"]}.{tid}.{oid}'
    what = objective['desc']
    embed = gen_obj_embed(objective, ctx.guild)
  if item_type == "task":
    task = item
    quest = quest_settings['quests'][task['qid']]
    tid = quest['tasks'].index(task) + 1
    idstr = f'{quest["id"]}.{tid}'
    what = task['name']
    embed = gen_task_embed(task, ctx.guild)
  else:
    idstr = quest['id']
    what = quest['name']
    embed = await new_quest_embed(quest, ctx.guild)
  
  quest_owner = ctx.guild.get_member(int(quest['owner']))
  if not quest_is_available(quest):
    return await ctx.reply(f"Quest **{quest['id']}. {quest['name']}** was taken down or has expired! Contact Quest Master **{quest_owner.display_name}** if you'd like it reposted.")

  author = ctx.message.author
  player = get_player(author)
  make_open_party_quest = False

  # player hasn't acccepted quest
  if author.id not in quest['playing']:
    # quest not open
    if quest['options']['party'] != 0:
      return await ctx.reply(f"You have not accepted this quest yet! You must first accept it with `{bot.prefix}quest accept {quest['id']} [..party member mentions]` before claiming tasks on this quest!")
    else:
      make_open_party_quest = True
  else:
    party_quest = ongoing_quests[quest['playing'][player['id']]]
  

  embed_msg = await ctx.reply(embed=embed)
  if make_open_party_quest:
    if quest['playing']:
      oqc = list(quest['playing'].values())[0]
      party_quest = ongoing_quests[oqc]
      if player['id'] not in party_quest['party']:
        party_quest['party'][player['id']] = 0
        quest['playing'][player['id']] = oqc
        player['active'][quest['id']] = oqc
        quest_settings['players'][player['id']] = player
    else:
      oqc = quest_settings['ongoing_quest_counter']
      quest_settings['ongoing_quest_counter'] += 1
      party_quest = {
        'id': oqc,
        'qid': quest['id'],
        'party': {str(author.id): 0}, 
        'tasks': {},
      }
      quest['playing'][player['id']] = oqc
      player['active'][quest['id']] = oqc
      quest_settings['players'][player['id']] = player
      ongoing_quests[oqc] = party_quest
      # save_quests() save at end. ensure no await tho
  # TODO: elif quest progressive and prev task not completed

  target = party_quest
  if objective:
    target = party_quest['tasks'].set_default(str(tid),{'objectives': {}})['objectives'].set_default(str(oid), {})
  elif task:
    target = party_quest['tasks'].set_default(str(tid), {})
  claim = target.set_default('claim', {'owner': None})

  oclaim_embed = None
  replace = False
  if claim['owner'] is not None and claim['owner'] != player['id']:
    try:
      oclaim_channel = ctx.guild.get_channel(int(claim['channel']))
      oclaim_msg = oclaim_channel.get_message(int(claim['msg']))
    except:
      target['claim'] = {'owner': None}
    else:
      replace = True
      owner = ctx.guild.get_member(int(claim['owner']))
      msg = await ctx.reply(f"{author.mention} is trying to claim {item_type} {idstr} but {owner.mention} has already claimed it. {owner.mention}, would you like to replace your claim with theirs? ({author.mention}, you can cancel this too by clicking :x:)",
        embed=discord.Embed(title="jump to original claim", url=oclaim_msg.jump_url)
      )
      await msg.add_reaction('???')
      await msg.add_reaction('???')
      response = {}
      def reaction_curry(r):
        def radd(reaction, user):
          if r == '???' and user.id == author.id:
            return
          response['r'] = r
          response['user'] = user
          return r
        return radd
      adds = {r: reaction_curry(r) for r in '??????'}

      try:
        await reaction_menu(ctx, msg, adds, {}, [author, owner], timeout=60*5)
      except asyncio.TimeoutError:
        await msg.reply('Did not receive a response for this. Try again.')
        await embed_msg.delete()
        return
      if response['r'] == '???':
        await msg.reply(f"{response['user'].mention} canceled this claim.")
        await embed_msg.delete()
        return
      # mark claim as not relevant anymore
      await oclaim_msg.add_reaction('????')
  elif claim['owner'] == player['id']:
    try:
      oclaim_channel = ctx.guild.get_channel(int(claim['channel']))
      oclaim_msg = oclaim_channel.get_message(int(claim['msg']))
    except:
      target['claim'] = {'owner': None}
    else:
      replace = True
      oclaim_embed = discord.Embed(title="jump to original claim", url=oclaim_msg.jump_url)
  
  # is owner or new.. or owner agreed to replace it
  claim['owner'] = player['id']
  claim['channel'] = str(ctx.channel.id)
  claim['msg'] = str(ctx.message.id)
  claim['members'] = list(set([player['id'], *participants])) if participants else [player['id']]
  claim['verified'] = False
  claim['desc'] = description
  claim['attachments'] = [
    {
      'file': a.filename, 
      'id': a.id
    }
    for a in ctx.message.attachments
  ]
  claim['what'] = what
  claim['owner_notif'] = None
  claim['notif_imgs'] = None
  claim['id_path'] = idstr
  claim['pqid'] = party_quest['id']
  quest_settings['claims'][claim['msg']] = {
    'pqid': party_quest['id'], 
    'id_path': idstr
  }
  save_quests()
  embed = await gen_claim_embed(claim, ctx.guild)
  try:
    msg = await quest_owner.send(embed=embed)
    claim['owner_notif'] = str(msg.id)
    quest_settings['claims'][str(msg.id)] = {'msg': claim['msg']}
    if ctx.message.attachments:
      atts = '\n'.join([a.url for a in ctx.message.attachments])
      msg = await msg.reply(f"Attached images: {atts}")
      claim['notif_imgs'] = str(msg.id)
      quest_settings['claims'][str(msg.id)] = {'msg': claim['msg']}
  except:
    pass

  await ctx.reply(f"You've claimed {item_type} **{idstr}**{' (replacing the previous claim)' if replace else ''}! {quest_owner.mention} will verify it soon.", embed=oclaim_embed)

@quest.command()
@is_quest_master_or_admin()
async def decline(ctx, *message_id: discord.Message):
  """Decline a Claim by an adventurer.

  Specify the claim to decline by writing your .quest decline message as a reply to the claim message.

  In order to decline multiple claims at once, you'll need to use message ids instead of replies. Get them by right clicking the .quest claim message (or notification) and clicking "Copy ID". To see this option, you may need to turn on Developer Mode in your discord settings > App Settings > Advanced.

  Example:
    .quest decline  <-- as a reply to the claim msg (or notification)
    .quest decline 919751809344622673 919761722800209961
  """
  msgs = message_id 
  # I missed that
  # julius ceaser dressing is for plebs
  # touche
  # :P we don't get chat points here
  if ctx.message.reference:
    reply = await ctx.guild.get_channel(ctx.message.reference.channel_id).fetch_message(ctx.message.reference.message_id)
    msgs = [reply, msgs*]
  msgs = list(set(msgs))
  
  


@quest.command()
@is_quest_master_or_admin()
async def verify(ctx, *message_id: discord.Message):
  """Verify a Claim by an adventurer.

  Specify the claim to verify by writing your .quest verify message as a reply to the claim message.

  In order to verify multiple claims at once, you'll need to use message ids instead of replies. Get them by right clicking the .quest claim message (or notification) and clicking "Copy ID". To see this option, you may need to turn on Developer Mode in your discord settings > App Settings > Advanced.

  Example:
    .quest verify  <-- as a reply to the claim msg (or notification)
    .quest verify 919751809344622673 919761722800209961
  """
  pass

# @quest.command()
# async def leaderboard(ctx):
#   """Shows You the Leaderboard of Global Level or Specified Quest XP!

#   Example:
#   .quest leaderboard Enchantment Table!.Diamonds!
#   """
#   pass

# @quest.command()
# async def notify(ctx):
#   """Notifys Members with Quests Posts matching specified Parameters!

#   Example:
#   .quest notify Miner Diamonds Breazy Solo
#   """
#   pass

def gen_task_embed(task, guild):
  q = quest_settings['quests'][str(task['qid'])]
  try:
    tn = q['tasks'].index(task) + 1
  except:
    tn = len(q['tasks']) + 1
  
  desc = task['desc']
  if task['xp']:
    desc += f'\n**{task["xp"]}** Bonus XP once completed ????'
  objs = task['objectives']
  space = "\u200c "
  if objs:
    desc += '\n\n__**Objectives:**__'
    for c, ob in enumerate(objs):
      start = f"{space*2}**{c+1}.** {space}"
      ms = start
      ms += ob['desc']
      if ob['xp']:
        ms += f" ({ob['xp']} xp)"
      
      ms, *subs_lines = ms.split('\n')
      ms = textwrap.fill(ms, width=80, initial_indent='', subsequent_indent=f'{space*10}')
      if subs_lines:
        ms += '\n' + '\n'.join(textwrap.fill(l, width=80, initial_indent=f'{space*10}', subsequent_indent=f'{space*10}') for l in subs_lines)
      
      desc += '\n' + ms
      

    # for l in o[1].split()
    #  + '\n'.join(f"{space*2}**.{c+1}** " + (f"({o[0]} xp) " if o[0] else "") + '\n'.join([l for l in enumerate(o[1].split('\n')]) for c, o in enumerate(objs))

  embed = discord.Embed(
    title=f"Task {task['qid']}.{tn} {task['name']}",
    description=desc,
    color=get_quest_author(q, guild).color
  )
  return embed

def gen_obj_embed(obj, guild):
  obj, task = obj
  q = quest_settings['quests'][str(task['qid'])]
  tn = q['tasks'].index(task) + 1
  on = task['objectives'].index(obj) + 1
  desc = f"__{task['name']}__\n{obj['desc']}"
  if obj['xp']:
    desc += f" ({obj['xp']}) xp"
  embed = discord.Embed(
    title=f"{task['qid']}.{tn}.{on} {q['name']}",
    description=desc,
    color=get_quest_author(q, guild).color
  )
  return embed

async def gen_claim_embed(claim, guild):
  channel = guild.get_channel(claim['channel'])
  cmsg = await channel.fetch_message(claim['msg'])
  author = guild.get_member(int(claim['owner']))
  embed = discord.Embed(
    title=f"Claimed {claim['id_path']} {claim['what']}",
    url=cmsg.jump_url,
    description=claim['desc'],
    color=cmsg.author.color
  ).set_author(
    name=author.display_name,
    icon_url=author.avatar_url,
  )
  if len(claim['members']) > 1:
    embed.set_footer(text=f"Claimed by {'@' + guild.get_member(int(m)).display_name for m in claim['members']}")
  return embed

@quest.group()
async def task(ctx):
  """commands for managing quest tasks
  """
  pass

@task.command(name="add")
async def task_add(ctx, quest_number: questPartConverterFactory(1), *, task_blurb: TaskConverter):
  """adds a new task to the specified quest.

  write tasks in the following format:

  <title>
  [xp=task bonus xp]
  [description]
  [objective list]
  
  objectives should be in the format:
  [xp for completing objective]-<objective description>

  Example:
    .quest task add 3 Firework Ingredients
    xp=20
    We'll need fireworks to celebrate
    20-1s gunpowder
    hint: ghasts or creepers
    10-1s paper
    -1s worth of assorted dyes
  """
  quest, _ = quest_number
  task = task_blurb
  task['qid'] = quest['id']
  embed = gen_task_embed(task, ctx.guild)
  msg = await ctx.reply("How's this?", embed=embed)
  resp = await wait_for_reaction_response(
      ctx, msg, ['???', '???'], 
      from_members=[ctx.message.author],
      timeout=60*2
  )
  if resp is None:
    return await msg.reply("Took too long to react. Try again later")
  if resp != '???':
    await msg.edit(content="Canceled.", embed=None)
    return
  quest['tasks'].append(task)
  save_quests()
  await ctx.send(f"Task {quest['id']}.{len(quest['tasks'])} added.")



@task.command(name="set")
async def task_set(ctx):
  """Allows you to edit a Task!

Example:
  .quest task set 3.2 add XP 75
  """
  pass

@task.command(name="delete")
async def task_delete(ctx):
  """Deletes the mentioned Task!

 Example:
 .quest delete 3.2
  """
  pass


TIME_PHRASE_PATTERN = re.compile(
    r"\b(((?P<dow>mon|tue|wed|thu|fri|sat|sun)(sday|nesday|rsday|urday|day)?)|"
    r"((?P<hour>1?[0-9])(:(?P<min>[0-5][0-9]))?\s?(?P<pm>am|pm))|"
    r"(?P<today>today|tomorrow|yesterday)|"
    r"((?P<th>[1-3]?[0-9])(th|st|rd|nd))|"
    r"((?P<month>1?[0-9])\/(?P<day>[0-3]?[0-9])(\/((20)?(?P<year>[0-9]{2})))?)|"
    r"(in (?P<rel>[0-9]+) (?P<rel_span>minute|hour|day|week)s?)|"
    r")\b")


def handle_time_change(change_dict, to_change, tz, future=True):
  n = to_change
  dow_map = {k:c for c,k in enumerate(['mon','tue','wed','thu','fri','sat','sun'])}
  today_map = {'yesterday': -1, 'today': 0, 'tomorrow': 1}
  if 'dow' in change_dict:
    target = dow_map[change_dict['dow']]
    n = n + timedelta(days=1)
    while n.weekday() != target:
      n = n + timedelta(days=1)
  elif 'today' in change_dict:
    n = n.replace(day=datetime.now().day + today_map[change_dict['today']])
  elif 'th' in change_dict:
    nd = n.replace(day=int(change_dict['th']))
    if nd <= n:
      if n.month == 12:
        nd = nd.replace(year=n.year+1, month=1)
      else:
        nd = nd.replace(month=n.month+1)
    n = nd
  elif 'hour' in change_dict:
    hr = int(change_dict['hour'])
    if hr == 12:
      hr = 0
    if change_dict['pm'] == 'pm':
      hr += 12
      hr %= 24
    mn = int(change_dict.get('min', 0))
    nd = n.replace(hour=hr, minute=mn)
    if future:
      if nd < n:
        nd += timedelta(days=1)
    n = nd
  elif 'month' in change_dict:
    year = int(change_dict.get('year', datetime.now().year))
    if year < 2000:
      year += 2000
    mon = int(change_dict['month'])
    day = int(change_dict['day'])
    n = n.replace(year=year, month=mon, day=day)
  elif 'rel' in change_dict:
    n = n + timedelta(**{(change_dict['rel_span']+'s'): int(change_dict['rel'])})
  return n


def get_hammertime_tz(ctx, author):
  try:
    return pytz.timezone(bot_settings['hammertime']['users'][str(author.id)])
  except KeyError:
    mr = set(str(r.id) for r in author.roles).intersection(bot_settings['hammertime']['roles'])
    if mr:
      return pytz.timezone(bot_settings['hammertime']['roles'][mr.pop()])
    return None
  
REACTION_ROLE_CHANNEL="<#740139001331187775>"

@bot.command(aliases=['hammerwhen', 'ht', 'hw'])
async def hammertime(ctx, *, time_phrase:str=None):
  """Stop. Hammertime.

  Use this command as a reply to a non-hammertime message sent by someone.. or use it with a time phrase to be converted to hammertime.

  unless specified with "yesterday" or a specific date, all dates/times are assumed to be in the future. 

  Example:
    .hammertime  <-- as a reply to a scrub
    .hammerwhen  <-- displays a relative time
    .hammertime sunday 1pm
    .hammertime 4pm
    .hammertime tomorrow at 10am
    .hammertime 9pm on the 9th
    .hammertime 5pm or 7pm
    .hammertime in 6 days  <-- minutes/hours/days/weeks
    when in doubt use this format:
    .hammertime 1/15/2022 5:30pm

  *pst: add a \ right after your .hammertime command to spit out a copyable version of the time to put in announcements n such:
  .hammertime \ wanna get pancakes sunday at 5pm?
  .hammertime \ <-- as a reply

  **pst: put a @mention in your .hammertime command to use their timezone instead. this doesn't work with replies though.

  credit: https://hammertime.djdavid98.art/
  """
  author = ctx.message.author  
  if ctx.message.mentions:
    author = ctx.message.mentions[0]
  slash = time_phrase and time_phrase.startswith('\\')
  if time_phrase is None or time_phrase == '\\':
    if not ctx.message.reference:
      return await ctx.reply('if no time phrase is given, you must give a replied message to hammertime.')
    msg = await ctx.guild.get_channel(ctx.message.reference.channel_id).fetch_message(ctx.message.reference.message_id)
    time_phrase = msg.content
    author = msg.author

  tz = get_hammertime_tz(ctx, author)
  if tz is None:
    return await ctx.reply(f'{author.mention} has not yet set their timezone role in {REACTION_ROLE_CHANNEL} or set their custom timzeone via `{bot.prefix}timezone`, so your guess is as good as mine.')

  tp = time_phrase.lower()

  when = ctx.invoked_with in ('hammerwhen', 'hw')

  if tp.startswith((
    'half-life 3',
    'half life 3',
    'halflife 3',
    'is half-life 3 coming out',
    'is half life 3 coming out',
    'is halflife 3 coming out',
    'is half life 3 coming out',
    "green and breazy's chess match",
    "breazy and green's chess match",
    "green's chess match",
    "breazy's chess match",
    'will green and breazy do their chess match',
    'will breazy and green do their chess match',
    'will green do his chess match',
    'will green do their chess match',
    'will breazy do his chess match'
  )):
    if when:
      return await ctx.send('<t:999999999999:R>')
    else:
      return await ctx.send('<t:999999999999>')
    

  onow = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
  
  times = []
  unfinished_times = []
  unfinished_dates = []
  o_time_obj = {
    'dt': None,
    'format': None
  }
  prev_time={'fmt':0, 'dt':onow}
  prev_date={'fmt':0, 'dt':onow}

  fmt_map = {
    'dow': 'F',
    'th': 'D',
    'today': 'D',
    'month': 'D',
    'rel': 'D',
    'hour': 't',
  }
  fmt_map = ('t','D','f','F')

  append_dt = None
  time_obj = deepcopy(o_time_obj)
  for match in TIME_PHRASE_PATTERN.finditer(tp):
    found = {k:v for k,v in match.groupdict().items() if v is not None}
    if not found:
      continue
    if 'rel' in found:
      if found['rel_span'] in ('minute', 'hour'):
        append_dt = {'fmt': 1,
          'dt': handle_time_change(found, onow, tz)}
      else:  # week, day
        unfinished_dates.append({'fmt': 2,
          'dt': handle_time_change(found, onow, tz)})
    elif 'hour' in found:
      unfinished_times.append({'fmt': 1,
        'dt': handle_time_change(found, onow, tz)})
    else:
      unfinished_dates.append({
        'fmt': 4 if 'dow' in found else 2,
        'dt': handle_time_change(found, onow, tz)
      })

    if append_dt:
      if len(unfinished_times) + len(unfinished_dates) >= 1:
        if len(unfinished_times) == 0:
          unfinished_times.append(prev_time)
        elif len(unfinished_dates) == 0:
          unfinished_dates.append(prev_date)
      else:
        times.append(append_dt)
        append_dt = None

    if len(unfinished_times) >= 1 and len(unfinished_dates) >= 1:
      for tm in unfinished_times:
        for dt in unfinished_dates:
          prev_date = dt
          prev_time = tm
          times.append({
            'dt': dt['dt'].replace(
              hour=tm['dt'].hour, 
              minute=tm['dt'].minute,
              second=tm['dt'].second),
            'fmt': min(4, dt['fmt'] + tm['fmt'])
          })
      unfinished_times = []
      unfinished_dates = []
      if append_dt:
        times.append(append_dt)
        append_dt = None

  # stragglers
  if len(unfinished_times) + len(unfinished_dates) >= 1:
    if len(unfinished_times) == 0:
      unfinished_times.append(prev_time)
    elif len(unfinished_dates) == 0:
      unfinished_dates.append(prev_date)
    for tm in unfinished_times:
      for dt in unfinished_dates:
        times.append({
          'dt': dt['dt'].replace(
            hour=tm['dt'].hour, 
            minute=tm['dt'].minute,
            second=tm['dt'].second),
          'fmt': min(4, dt['fmt'] + tm['fmt'])
        })
  
  # for t in times:
  #   t['dt'] = tz.localize(t['dt'])

  msg = '\n'.join(
    ('\\' if slash else '') + 
    f"<t:{int(t['dt'].timestamp())}:{'R' if when else fmt_map[t['fmt']-1]}>" for t in times
  )

  if not msg:
    return await ctx.reply(f'no time phrase was found. make sure you follow the format in `{bot.prefix}help hammertime`, you dingus.')

  await ctx.reply(msg)
  

@bot.command()
async def hammerthem(ctx, member: discord.Member):
  """what time is it for em?"""
  tz = get_hammertime_tz(ctx, member)
  if not tz:
    return await ctx.reply(f"heck if I know what time it is for em. **{member.display_name}** hasn't set their timezone yet. Yo {member.mention}, do us a favor and grab a timezone from {REACTION_ROLE_CHANNEL} or use the `{bot.prefix}timezone` command to set a custom one if your timezone isn't in that list.")
  tm = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
  await ctx.reply(f"**{member.display_name}** is in **{tz}**. It's **{tm.strftime('%A, %B')} {tm.day}, {tm.year} {int(tm.strftime('%I'))}:{tm.strftime('%M %p')}** for them right now.")

@bot.command()
async def timezone(ctx, timezone: str=None):
  """set your own timezone if it's not listed in #roles. leave timezone blank to remove it.
  
  Note: This overrides whatever timezone role you might have."""
  if timezone is None:
    if str(ctx.message.author.id) not in bot_settings['hammertime']['users']:
      return await ctx.reply("you already don't have a timezone set.")
    del bot_settings['hammertime']['users'][str(ctx.message.author.id)]
    save_bot_settings()
    return await ctx.reply('your custom timezone has been unset. If you have a timezone role set, it will be used when you use `.hammertime`.')
  else:
    if timezone not in pytz.all_timezones:
      return await ctx.reply(f'{timezone} {NOT_A_TIMEZONE_MSG}')
    bot_settings['hammertime']['users'][str(ctx.message.author.id)] = timezone
    save_bot_settings()
    await ctx.reply(f'Your timezone is set to **{timezone}**')

eval_data = {'_last_result': None}

# from Red
def cleanup_code(content):
    """removes code blocks from content string."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')

@bot.command(hidden=True, name='eval')
@commands.is_owner()
async def _eval(ctx, *, body: str):
    """Evaluates some code in an async function"""

    env = {
        'bot': bot,
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        '_': eval_data['_last_result']
    }

    env.update(globals())

    body = cleanup_code(body)
    stdout = io.StringIO()

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        try:
            await ctx.message.add_reaction('\u2705')
        except:
            pass

        if ret is None:
            if value:
                await ctx.send(f'```py\n{value}\n```')
        else:
            eval_data['_last_result'] = ret
            await ctx.send(f'```py\n{value}{ret}\n```')


# repost app
@bot.listen()
async def on_message(msg):
  # EasyApplication Bot in some hidden application channel
  if msg.author.id == 737539715854761994 and msg.channel.id == 801202454460760094:
    # submitted-apps channel
    target = msg.guild.get_channel(924764896929939506)
    if msg.embeds:
      for em in msg.embeds:
        m = await target.send(embed=em)
      for r in '??????????????':
        await m.add_reaction(r)
      # applicant_id = msg.embeds[0].description.split('<@')[-1].split('>')[0]
      # applicant_reaction_msg = m.id

playing_msgs = {}

ON_MINECRAFT_ROLE_ID = 925600205859074160
ON_MINCREAFT_LOG_CHANNEL = 811317212535062539
FUNKY = 675822019144712247


# member playing minecraft
@bot.listen()
async def on_member_update(before, after):
  bacts = sorted([a.name or str(a) for a in before.activities])
  aacts = sorted([a.name or str(a) for a in after.activities])
  if str(bacts) == str(aacts):
    return
  action = None
  emote = '???'
  if 'Minecraft' in bacts and 'Minecraft' not in aacts:
    emote = '????'
    action = '`stopped`'
  if 'Minecraft' not in bacts and 'Minecraft' in aacts:
    action = '__started__'
  if action is None:
    return
  
  log_channel = before.guild.get_channel(ON_MINCREAFT_LOG_CHANNEL)
  name = after.mention
  if check_is_admin(after):
    name = after.name
  tz = get_hammertime_tz(None, after)
  their_time = ''
  
  if tz:
    tm = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
    their_time = f" (**{tm.strftime('%A')} {int(tm.strftime('%I'))}:{tm.strftime('%M %p')}** their time)."

  s = f"{emote} {name} **{action}** at <t:{int(datetime.now().timestamp())}:F>{their_time}"
  # msg = playing_msgs.get(after.id)
  # if 'stopped' in action and msg:
  #   await msg.edit(msg.content + '\n' + s)
  # else:
  await log_channel.send(s)

  # On Minecraft role
  role = after.guild.get_role(ON_MINECRAFT_ROLE_ID)
  if 'stopped' in action:
    await after.remove_roles(role)
  else:
    await after.add_roles(role)


@bot.listen()
async def on_ready():
  # reset On Minecraft role members
  funky = bot.get_guild(675822019144712247)
  on_minecraft_role = funky.get_role(ON_MINECRAFT_ROLE_ID)
  marked = on_minecraft_role.members

  start_players = []
  end_players = []
  for m in funky.members:
    playing = 'Minecraft' in [a.name for a in m.activities]

    if playing:
      if m not in marked:
        start_players.append(m)
        await m.add_roles(on_minecraft_role)
    else:
      if m in marked:
        end_players.append(m)
        await m.remove_roles(on_minecraft_role)

  if start_players or end_players:
    s = f'**I missed a few changes while I was offline.** I noticed these changes at <t:{int(datetime.now().timestamp())}:F>'
    log_channel = bot.get_guild(FUNKY).get_channel(ON_MINCREAFT_LOG_CHANNEL)
    utc_now = datetime.utcnow()
    if start_players:
      s += '\n\n??? __Players playing Minecraft since I went offline:__'
      for p in start_players:
        name = p.mention
        if check_is_admin(p):
          name = p.name
        tz = get_hammertime_tz(None, p)
        their_time = ''
        
        if tz:
          tm = utc_now.replace(tzinfo=pytz.utc).astimezone(tz)
          their_time = f" (**{tm.strftime('%A')} {int(tm.strftime('%I'))}:{tm.strftime('%M %p')}** their time)."

        s += f"\n{name}{their_time}"
    if end_players:
      s += '\n\n???? __Players `stopped` playing Minecraft since I went offline:__'
      for p in start_players:
        name = p.mention
        if check_is_admin(p):
          name = p.name
        tz = get_hammertime_tz(None, p)
        their_time = ''
        
        if tz:
          tm = utc_now.replace(tzinfo=pytz.utc).astimezone(tz)
          their_time = f" (**{tm.strftime('%A')} {int(tm.strftime('%I'))}:{tm.strftime('%M %p')}** their time)."

        s += f"\n{name}{their_time}"
    await log_channel.send(s)

@bot.command()
async def quote(ctx, time = None):
  """
Reply to a Message with .quote to ???quote??? it. 
If you want the time there as well then use .quote time"""
  if not ctx.message.reference:
    return await ctx.reply("Ya gotta reply to a message")
  if time != None:
    reply = ctx.message.reference
    msg_ = await ctx.fetch_message((reply.message_id))
    msg_time = int((msg_.created_at).timestamp())
    await ctx.send(f'>>> {msg_.author} aka {msg_.author.nick} \n " **{msg_.content}**  " \n <t:{msg_time}:F>')
  if time == None:
    reply = ctx.message.reference
    msg_ = await ctx.fetch_message((reply.message_id))
    await ctx.send(f'>>> {msg_.author} aka {msg_.author.nick} \n " **{msg_.content}**  " ')


@bot.group(alises = ['scratchcard'])
async def scratchCards(ctx):
  """generates a scratchcard"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command) # i copied u this time :P


@scratchCards.command()
async def card(ctx):
  """ Power write me another help plz"""
  emoji_scratch = [':one:',':two:',':three:', '<:dogekek:740526136844615710>']
  lineCount = 0
  Scratchcard = str()
  sCount = 0
  # 5 lines
  while lineCount != 4:
    # grab 4 random things
    cardRandomiser = random.choices(emoji_scratch, k=4)
    # for each thing
    for s in list(cardRandomiser):
      sCount += 1
      Scratchcard += "|| " + s + " ||" # same thing
      # "||{}||".format(s) # same thing. it just sticks the thing into th string
      if sCount == 4: #ill try redo this tomorrow
        Scratchcard = Scratchcard + '\n'  
        sCount = 0
    # kk. try it out before you sleep :P
    # aight. go sleep :P
    # formatScratch = (''.join(f"||{s}||" for s in (Scratchcard))) # ah, see what you're doing is grabbing every letter in the string that is scratchcard. 
    lineCount += 1
  await ctx.send(f'>>> Scratch to win! \n {Scratchcard} ')
  
@scratchCards.command(name= 'check' )
async def checkScratch(ctx):
  """checks winning"""
  emoji_scratch = ['1','2','3','4']
  reply = ctx.message.reference
  ThingToCheck = await ctx.fetch_message((ctx.message_id)) #need to check if this is ac a thing to check
  scratchToCheck = await ctx.fetch_message((reply.message_id))

  



@bot.command()
async def doot(ctx):
  """Doot, thats it """
  await ctx.send(f' Daily <@396794458378731520> Doot')

@bot.command()
async def nerd(ctx):
  """Reply to someone and call them a nerd"""
  if not ctx.message.reference:
    await ctx.reply("Reply to a message. nerd")
  else:
    nerdReply = ctx.message.reference
    nerdMsg_ = await ctx.fetch_message((nerdReply.message_id))
    await ctx.send(f">>> <@{nerdMsg_.author.id}> You're a Nerd ")

@bot.group(aliases=['cc'])
async def customcommand(ctx):
  """add custom phrases n such to the bot"""
  if ctx.invoked_subcommand is None:
    await ctx.send_help(ctx.command)

@customcommand.command(name='list')
async def cc_list(ctx):
  """list the custom phrases the bot has. add more using customcommand set."""
  clist = bot.data['custom_commands']['triggers']
  s = textwrap.fill('  '.join([t for t in clist]), width=80)
  if not s:
    s = '[none]'
  await ctx.send(f'__**Custom Commands**__\n>>> **{s}**')

@customcommand.command(name='set', aliases=['add'])
@is_admin()
async def cc_set(ctx, trigger, *, phrase):
  """sets/adds a custom phrase to the bot. a list of these can be seen with customcommands list and can be used using the bot prefix followed by the custom command trigger."""
  trigger = trigger.lower()
  if phrase is None:
    return await ctx.reply("the phrase can't be empty")
  if trigger in [c.name.lower() for c in bot.commands]:
    return await ctx.reply("the trigger can't be an existing command")
  clist = bot.data['custom_commands']['triggers']
  if trigger in clist:
    resp = await wait_for_reaction_response(
      ctx, f"**{trigger}** is already a custom command trigger. replace it?", 
      ['???', '???'], from_members=[ctx.message.author],
      timeout=15
    )
    if resp is None:
      return await ctx.send("took too long to react. try again later")
    if resp != '???':
      return
  clist[trigger] = phrase
  save_data('custom_commands')
  await ctx.reply(f"**{trigger}** added as a custom command. type `{bot.prefix}{trigger}` to use it!")

@customcommand.command(name='remove', aliases=['rm'])
@is_admin()
async def cc_rm(ctx, trigger):
  clist = bot.data['custom_commands']['triggers']
  if trigger not in clist:
    return await ctx.reply(f"**{trigger}** is not a custom command")
  del clist[trigger]
  save_data('custom_commands')
  await ctx.reply(f"the custom command **{trigger}** was deleted.")

@bot.listen('on_message')
async def cc_on_message(msg):
  if not msg.content.startswith(bot.prefix):
    return
  mc = msg.content[len(bot.prefix):]
  clist = bot.data['custom_commands']['triggers']
  try:
    cmd = clist[mc.split(None, 1)[0]]
  except:
    return
  await msg.reply(cmd)

@bot.command()
async def poll(ctx, *reactions: RealEmojiConverter):
  """adds the reactions listed so you can be a part of the poll too. You can also use it to make yourself feel like ppl read and respond to your messages"""
  if not reactions:
    return await ctx.reply('you must specify some emojis to add')
  if len(reactions) > 10:
    return await ctx.reply(f"yo, {len(reactions)} reactions is excessive.")
  try:
    await ctx.message.clear_reactions()
  except:
    for r in reactions:
      await ctx.message.remove_reaction(r, bot.user)
  # copied this from you green, thats plagarism
  if not ctx.message.reference:
    return await ctx.reply("Ya gotta reply to a message")
  reply = ctx.message.reference
  msg = await ctx.fetch_message(reply.message_id)
  for r in reactions:
    try:
      await msg.add_reaction(r)
    except:
      pass



@bot.listen() # <-- this is an event listener instead of a command
async def on_ready():  # <-- wait for the bot to be ready
  # if 'restart_counter' doesn't exist in the db, put in an initial value
  if 'restart_counter' not in bot_settings:
    bot_settings['restart_counter'] = 1
    save_bot_settings()
  else: # otherwise, increment it
    bot_settings['restart_counter'] += 1
    save_bot_settings()

# copied from stack overflow :P
# https://stackoverflow.com/a/16671271
def number_th(n):
    """puts st, nd, rd, th at the end of numbers"""
    return str(n)+("th" if 4<=n%100<=20 else {1:"st",2:"nd",3:"rd"}.get(n%10, "th"))

@bot.command()
async def deaths(ctx):
  """how many times my creators have killed me and revived me"""
  await ctx.reply(f"Help me D: this is the {number_th(bot_settings['restart_counter'])} time my creators have killed me!")

async def ghost_doot():
  doots = [
    'Doot', 
    'dooot', 'd o o t', 'DoooOOOooot', 'dwoot', 'I am Sir DootsAlot III', 'doot doot','https://tenor.com/view/pingu-noot-noot-not-noot-sit-gif-21639411',
    'https://cdn.discordapp.com/attachments/922128872722546688/926970135586148383/dooot.gif'
  ]
  await bot.get_guild(675822019144712247).get_channel(922128872722546688).send(random.choice(doots))
bot.ghost_doot = ghost_doot




##### PLACES TO GET INFO #####
# dir(my_thing) - lists the attributes in my_thing
# help(my_thing) - displays help for my_thing
# discord api reference - https://discordpy.readthedocs.io/ - use this instead of dir/help for discord objects
# python visualization - https://pythontutor.com/ - use this to follow your program step by step and see what's going on
# google

# this runs the web server
server.keep_alive(bot)

bot.bot_settings = bot_settings
bot.quest_settings = quest_settings
bot.ongoing_quests = ongoing_quests

bot.run(my_secret, reconnect=True) # <-- reconnects if it disconnects