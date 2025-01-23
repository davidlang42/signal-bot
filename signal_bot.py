import os
import io
import base64
import subprocess
import json
import time
import datetime
import requests # pip install requests
import qrcode # pip install qrcode

TASK_EMOJI="☑️"
MESSAGES="/signal_bot_messages"
CONFIG="/signal_bot_config"
NAME_SEPARATOR=": "
MAX_TITLE_LENGTH=60
TITLE_TRUNCATION="..."

appsScriptUrl = os.getenv("GOOGLE_APPS_SCRIPT_URL")
if not appsScriptUrl:
     print("Must set environment variable GOOGLE_APPS_SCRIPT_URL")
     exit(1)

### Google Apps Scripts API

def SendEmail(subject, html):
    response = requests.get(appsScriptUrl, {
        'action':'email',
        'title': subject,
        'html': html
    })
    if response.status_code == 200:
        print(f"Sent email '{subject}'")
        return True
    else:
        print(f"Failed ({response.status_code}) to send email '{subject}': {response.text}")
        return False

def AddTask(title, notes):
    response = requests.get(appsScriptUrl, {
        'action':'task',
        'due': datetime.datetime.today().strftime('%Y-%m-%d'), #TODO might need to handle $DATE_ADJUSTMENT unless I can set container timezone
        'title': title,
        'notes': notes
    })
    if response.status_code == 200:
        print(f"Added task '{title}'")
        return True
    else:
        print(f"Failed ({response.status_code}) to add task '{title}': {response.text}")
        return False
    
### Monitor using signal-cli

def LinkDevice():
    process = subprocess.Popen(['signal-cli', '--config', CONFIG, 'link', '-n', "SignalBot"], stdout=subprocess.PIPE)
    link = process.stdout.readline().decode()
    qr = qrcode.make(link)
    memory_buffer = io.BytesIO()
    qr.save(memory_buffer, format="PNG")
    base64string = base64.b64encode(memory_buffer.getvalue()).decode()
    html = f'<p>{link}</p><img src="data:image/png;base64,{base64string}" />'
    if not SendEmail("SignalBot is not linked", html):
        print("Failed to send link email")
        process.terminate()
        return False
    returncode = process.wait()
    return returncode == 0

def ListenForMessages():
    return subprocess.Popen(['signal-cli', '--config', CONFIG, '-o', 'json', 'receive', '-t', '-1', '--ignore-attachments', '--ignore-stories', '--max-messages', '10'], stdout=subprocess.PIPE, universal_newlines=True)

def RemoveEmoji(author, receiver, timestamp):
    listener.terminate() # otherwise executing signal-cli below will fail
    subprocess.run(['signal-cli', '--config', CONFIG, 'sendReaction', '-r', '-e', TASK_EMOJI, '-t', timestamp, '-a', author, receiver])

### Parse JSON payloads

def ProcessPayload(p):
    if "envelope" in p:
        ProcessEnvelope(p["envelope"], p["account"])

def ProcessEnvelope(e, account):
    print(f"ENVELOPE: {e}") #TODO remove
    if "syncMessage" in e and "sentMessage" in e["syncMessage"]:
        # I sent a message or I reacted
        sent = e["syncMessage"]["sentMessage"]
        source = e["source"]
        dest = sent["destination"]
        if not dest:
            dest = sent["groupInfo"]["groupId"]
        if "message" in sent and sent["message"]:
            ProcessMessage(sent, source, dest, e["sourceName"])
        elif "reaction" in sent:
            ProcessReaction(sent["reaction"], source, dest)
    elif "dataMessage" in e:
        # they sent a messsage or they reacted (but ignore their reactions)
        received = e["dataMessage"]
        dest = account
        if "groupInfo" in received:
            dest = received["groupInfo"]["groupId"]
        if "message" in received and received["message"]:
            ProcessMessage(received, e["source"], dest, e["sourceName"])

def ProcessMessage(m, source, dest, name):
    message = m["message"]
    timestamp = m["timestamp"]
    StoreMessage(source, dest, timestamp, name, message)
    if "quote" in m:
        #TODO TEST THIS BRANCH
        reply = m["quote"]
        reply_to_author = reply["author"]
        reply_to_timestamp = reply["id"]
        reply_to_receiver = dest
        if reply_to_author == reply_to_receiver:
            reply_to_receiver = source
        previous_message = ReadMessage(reply_to_author, reply_to_receiver, reply_to_timestamp)
        if previous_message:
            AppendMessage(source, dest, timestamp, previous_message)
    HandleMessage(source, dest, timestamp, message)

def ProcessReaction(reaction, source, dest):
    emoji = reaction["emoji"]
    is_remove = reaction["isRemove"]
    author = reaction["targetAuthor"]
    timestamp = reaction["targetSentTimestamp"]
    if author == dest:
        dest = source
    HandleReaction(author, dest, timestamp, emoji, is_remove)

### Persist messages by (author, receiver, timestamp)

def StoreMessage(author, receiver, timestamp, name, message):
    heading = (message[:MAX_TITLE_LENGTH-len(TITLE_TRUNCATION)] + TITLE_TRUNCATION) if len(message) > MAX_TITLE_LENGTH else message
    body = name + NAME_SEPARATOR + message
    with open(MessagePath(author, receiver, timestamp), 'w') as f:
        f.write(heading + '\n')
        f.write(body + '\n')

def AppendMessage(author, receiver, timestamp, previous_message):
    append_lines = previous_message.splitlines()[1:] # skip the first line (heading) of previous_message, we only want to append the body
    with open(MessagePath(author, receiver, timestamp), 'a') as f:
        for line in append_lines:
            f.write(line + '\n')

def ReadMessage(author, receiver, timestamp):
    path = MessagePath(author, receiver, timestamp)
    if not os.path.isfile(path):
        return None
    with open(path, 'r') as f:
        return f.read()

def MessagePath(author, receiver, timestamp):
    folder = os.path.join(MESSAGES, author, receiver)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, str(timestamp))

### Actually be a Signal bot

def HandleMessage(author, receiver, timestamp, message):
    # either I sent a message, or someone sent a message to me/group
    pass

def HandleReaction(author, receiver, timestamp, emoji, is_remove):
    # I either reacted to my own message, or one sent to me/group
    if emoji == TASK_EMOJI and not is_remove:
        lines = ReadMessage(author, receiver, timestamp)
        if len(lines) < 1:
            name = "Unknown Task"
            notes = f"Signal message from {author} to {receiver} at {timestamp} could not be found"
        else:
            name = lines[0]
            notes = lines[1:]
        if AddTask(name, notes):
            RemoveEmoji(author, receiver, timestamp)

### Main loop

while True:
    listener = ListenForMessages() # global so RemoveEmoji can terminate it
    for line in iter(listener.stdout.readline, ""):
        ProcessPayload(json.loads(line))
    if listener.wait() != 0: # non-zero return code indicates device is not linked
        if not LinkDevice(): # tries for 1min
            time.sleep(4 * 60) # wait 1+4min between repeated link emails
