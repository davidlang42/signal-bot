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
    
### Interact with signal-cli

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

#TODO TEST BELOW HERE

def ProcessEnvelope(e, account):
    print(f"ENVELOPE: {e}")
    if "syncMessage" in e and "sentMessage" in e["syncMessage"]:
        # I sent a message or I reacted
        sent = e["syncMessage"]["sentMessage"]
        source = e["source"]
        dest = sent["destination"]
        CheckMessageForContent(sent, source, dest, e["sourceName"])
        CheckMessageForReaction(sent, source, dest)
    elif "dataMessage" in e:
        # they sent a messsage or they reacted (but ignore their reactions)
        CheckMessageForContent(e["dataMessage"], e["source"], account, e["sourceName"])

def CheckMessageForContent(m, source, dest, name):#TODO rename and revise args
    print(f"CHECK-MSG-CONTENT: {m}")
    if not "message" in m:
        return
    message = m["message"]
    timestamp = m["timestamp"]
    StoreMessage(source, dest, timestamp, name, message)
    if "quote" in m:
        #TODO revise this branch (needs testing)
        reply = m["quote"]
        reply_to_author = reply["author"]
        reply_to_timestamp = reply["id"]
        reply_to_receiver = dest
        if reply_to_author == reply_to_receiver:
            reply_to_receiver = source
        previous_message = ReadMessage(reply_to_author, reply_to_receiver, reply_to_timestamp)
        AppendMessage(source, dest, timestamp, previous_message)

def CheckMessageForReaction(m, source, dest):#TODO rename and revise args
    print(f"CHECK-MSG-REACTION: {m}")
    if not "reaction" in m:
        return
    reaction = m["reaction"]
    emoji = reaction["emoji"]
    remove = reaction["isRemove"]
    if emoji == TASK_EMOJI and not remove:
        author = reaction["targetAuthor"]
        timestamp = reaction["targetSentTimestamp"]
        if author == dest:
            HandleReaction(author, source, timestamp)
        else:
            HandleReaction(author, dest, timestamp)

### Persist messages by (author, receiver, timestamp)

def StoreMessage(author, receiver, timestamp, name, message):
    print(f'[{author}, {receiver}, {timestamp}] {name}{NAME_SEPARATOR}{message}') #TODO remove
    heading = (message[:MAX_TITLE_LENGTH-len(TITLE_TRUNCATION)] + TITLE_TRUNCATION) if len(message) > MAX_TITLE_LENGTH else message
    body = name + NAME_SEPARATOR + message
    #TODO: echo "$1" > "$(message_path "$2" "$3" "$4")"
    #TODO: echo "(Signal message $5)" >> "$(message_path "$2" "$3" "$4")"

def AppendMessage(author, receiver, timestamp, previous_message):
    print(f'TODO---APPEND: {previous_message}')
    #TODO: skip the first line of previous_message, because thats just the (truncated) heading
    #TODO: echo "$1" >> "$(message_path "$2" "$3" "$4")"

def ReadMessage(author, receiver, timestamp):
    print(f'TODO---READ')
    #TODO: read the whole thing, including the (truncated) heading on the first line
    #TODO: cat "$(message_path "$1" "$2" "$3")"

def MessagePath(author, receiver, timestamp):
    return f"{MESSAGES}/{author}_{receiver}_{timestamp}"

### Actually be a Signal bot

def HandleReaction(author, receiver, timestamp):
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
