from flask import Flask
from threading import Thread
import pprint

pp = pprint.PrettyPrinter(indent=4, sort_dicts=False)
vars = {
  'doot': False,
  'bot': None
}

app = Flask(__name__)

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