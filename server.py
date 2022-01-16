import os
from flask import Flask, session, redirect, request, url_for, jsonify
from requests_oauthlib import OAuth2Session
from threading import Thread
import pprint

OAUTH2_CLIENT_ID = os.environ['OAUTH2_CLIENT_ID']
OAUTH2_CLIENT_SECRET = os.environ['OAUTH2_CLIENT_SECRET']
OAUTH2_REDIRECT_URI = 'https://FunkyBot.funkydevs.repl.co/callback'
FLASK_SECRET_KEY = os.environ['FLASK_SECRET_KEY']

API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'

pp = pprint.PrettyPrinter(indent=4, sort_dicts=False)
vars = {
  'doot': False,
  'bot': None
}

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

@app.route('/')
def main():
    return """
    <html>
    <script>
    async function doot() {
      document.getElementById("doot").disabled = true
      await fetch('doot');
      setTimeout(() => {
        document.getElementById("doot").disabled = false
      }, 10000)
    }
    </script>
    <button id="doot" onclick="doot()">doot</button>
    </html>
    """

@app.route('/doot')
def doot():
    vars['bot'].loop.create_task(vars['bot'].ghost_doot())
    return "doot"


def token_updater(token):
    session['oauth2_token'] = token


def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater)


@app.route('/login')
def index():
    scope = ['identify']
    discord = make_session(scope=scope)
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)


@app.route('/callback')
def callback():
    if request.values.get('error'):
        return request.values['error']
    discord = make_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url.replace('http://', 'https://'))
    session['oauth2_token'] = token
    return redirect(url_for('.me'))


@app.route('/me')
def me():
    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(API_BASE_URL + '/users/@me').json()
    bot = vars['bot']
    funky = bot.get_guild(675822019144712247)
    member = funky.get_member(int(user['id']))
    obj = {
      'name': member.display_name,
      'roles': [
        {
          'name': role.name,
          'color': (role.color.r, role.color.g, role.color.b) if sum([role.color.r, role.color.g, role.color.b]) != 0 else (100,100,100)
        }
        for role in member.roles
      ],
      'is_admin': bot.check_is_admin(member),
      'is_quest_master': bot.check_is_quest_master(member)
    }
    html = f"""<html>
    <h2>@{obj['name']}</h2>
    <ul style="list-style-type:none;font-size:12;display:inline;">
    {''.join(['<li style="color:#{:02x}{:02x}{:02x};'.format(255,255,255) + 'display:inline-block;border-radius:3px;padding:3px;margin-top:3px;background:#{:02x}{:02x}{:02x}'.format(*r['color']) + '">@' + r['name']+ "</li></br>" for r in obj['roles']])}
    </ul>
    </html>
    """
    
    return html  #jsonify(user=obj)


@app.route('/quests/<qid>', methods=['GET'])
def quests(qid):
    quests = {k: v for k, v in vars['bot'].quest_settings['quests'].items()}
    print(quests)
    print('----')
    pf = pp.pformat(dict(quests[qid]))
    print(pf)
    return f'<pre>{pf}</pre>'

def run():
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)

def keep_alive(bot):
    vars['bot'] = bot
    server = Thread(target=run)
    server.start()