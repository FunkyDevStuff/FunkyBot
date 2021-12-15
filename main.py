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
import pytz
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

SPAN_PATTERN = re.compile(r'(?P<amt>[0-9]+)(?P<span>[dw])')

def parse_delta(s):
  if s == '0':
    return 0
  m = SPAN_PATTERN.match(s)
  if not m:
    raise commands.ArgumentParsingError(f'{s} is not a valid timespan format.')
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
      raise commands.ArgumentParsingError(f'{s} is less than the minimum value {minv}')
    if days > mx:
      raise commands.ArgumentParsingError(f'{s} is greater than the minimum value {maxv}')
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

@bot.command(name="error")
@is_admin()
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
  options = options.strip()
  name, *options = [o.strip() for o in options.split('\n')]
  

  await ctx.send(f'name: {name}\noptions: {options}')


@quest.command()
async def list(ctx, search_term: str=None, sort_by: str=None):
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
  pass

@quest.command() 
async def info(ctx, quest_id: str):
  """Shows info about a quest listed in .quest list. 
  You can also use this command to check the progress of quests you've accepted.

  quest_id is the quest number. It can be made more specific by adding task and objective numbers separated by periods.
 
  Examples:
    .quest info 2      <-- quest 2
    .quest info 5.2.3  <-- quest 5, task 2, objective 3
  """
  pass

@quest.command()
async def accept(ctx, quest_number: int, * party_members: discord.Member):
  """Accept a Quest by yourself or with Party Members!

  party members must hm?
  
  Example:
    .quest accept 2 @.Power @Deno
    .quest accept 3
  """
  pass

@quest.command(name="set")
async def quest_set(ctx):
  """Commands to change options on your quests before you post them. 
  Some options can still be changed after publishing but be considerate of Adventurers that may be taking the Quest at that time.
  """
  pass

@quest.command()
async def claim(ctx, quest_id: str, description: str=None):
  """Claim a Quest/Track with a description to await Verification!

  Example:
    .quest claim 4.3 The Diamonds are in the Mailbox!
    .quest claim 1.2.4 <picture of music discs>
  """
  pass

@quest.command()
@is_quest_master_or_admin()
async def verify(ctx, *message_id: discord.Message):
  """Verify a Claim by an adventurer.

  Specify the claim to verify by writing your .quest verify message as a reply to the claim message.

  In order to verify multiple claims at once, you'll need to us message ids instead of replies. Get them by right clicking the .quest claim message and clicking "Copy ID". To see this option, you may need to turn on Developer Mode in your discord settings > App Settings > Advanced.

  Example:
    .quest verify  <-- as a reply to the claim msg
    .quest verify 919751809344622673 919761722800209961
  """
  pass

@quest.command()
async def leaderboard(ctx):
  """Shows You the Leaderboard of Global Level or Specified Quest XP!

  Example:
  .quest leaderboard Enchantment Table!.Diamonds!
  """
  pass

@quest.command()
async def notify(ctx):
  """Notifys Members with Quests Posts matching specified Parameters!

  Example:
  .quest notify Miner Diamonds Breazy Solo
  """
  pass

@quest.group()
async def task(ctx):
  """Help
  """
  pass

@task.command(name="add")
async def task_add(ctx):
  """Create a new numbered Task within a stated Quest!

Example:
.quest task add 3.1 XP50

 """
  pass

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

  credit: https://hammertime.djdavid98.art/
  """
  author = ctx.message.author
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
  for match in TIME_PHRASE_PATTERN.finditer(time_phrase):
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


# this runs the web server
server.keep_alive()

bot.run(my_secret, reconnect=True) # <-- reconnects if it disconnects