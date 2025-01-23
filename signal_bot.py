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

appsScriptUrl = os.getenv("GOOGLE_APPS_SCRIPT_URL")
if not appsScriptUrl:
     print("Must set environment variable GOOGLE_APPS_SCRIPT_URL")
     exit(1)

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

#TODO TEST BELOW HERE

def ProcessPayload(p):
    print(f"PAYLOAD: {p}")
    if "envelope" in p:
        ProcessEnvelope(p["envelope"], p["account"])

def ProcessEnvelope(e, account):
    print(f"ENVELOPE: {e}")
    source = e["source"]
    if "syncMessage" in e and "sentMessage" in e["syncMessage"]:
        # I sent a message or I reacted
        sent = e["syncMessage"]["sentMessage"]
        dest = sent["destination"]
        CheckMessageForContent(sent, source, dest, f"to {dest}")
        CheckMessageForReaction(sent, source, dest)
    if "dataMessage" in e:
        # they sent a messsage or they reacted (but ignore their reactions)
        received = e["dataMessage"]
        source_name = e["sourceName"]
        CheckMessageForContent(received, source, account, f"from {source_name}")

def CheckMessageForContent(m, source, dest, from_to_display_name):
    print(f"CHECK-MSG-CONTENT: {m}")
    if not "message" in m:
        return
    message = m["message"]
    timestamp = m["timestamp"]
    StoreMessage(message, source, dest, timestamp, from_to_display_name)
    if "quote" in m:
        reply = m["quote"]
        reply_to_author = reply["author"]
        reply_to_timestamp = reply["id"]
        reply_to_receiver = dest
        if reply_to_author == reply_to_receiver:
            reply_to_receiver = source
        previous_message = ReadMessage(reply_to_author, reply_to_receiver, reply_to_timestamp)
        AppendMessage(previous_message, source, dest, timestamp)

def CheckMessageForReaction(m, source, dest):
    print(f"CHECK-MSG-REACTION: {m}")
    if not "reaction" in m:
        return
    emoji = m["reaction"]["emoji"]
    remove = m["reaction"]["isRemove"]
    if emoji == TASK_EMOJI and not remove:
        author = m["reaction"]["targetAuthor"]
        timestamp = m["reaction"]["targetSentTimestamp"]
        if author == dest:
            HandleReaction(author, source, timestamp)
        else:
            HandleReaction(author, dest, timestamp)

def StoreMessage(message, author, receiver, timestamp, from_to_display_name):
    print(f'TODO---STORE: {message}')
    #TODO: echo "$1" > "$(message_path "$2" "$3" "$4")"
    #TODO: echo "(Signal message $5)" >> "$(message_path "$2" "$3" "$4")"

def AppendMessage(message, author, receiver, timestamp):
    print(f'TODO---APPEND: {message}')
    #TODO: echo "$1" >> "$(message_path "$2" "$3" "$4")"

def ReadMessage(author, receiver, timestamp):
    print(f'TODO---READ')
    #TODO: cat "$(message_path "$1" "$2" "$3")"

def MessagePath(author, receiver, timestamp):
    return f"{MESSAGES}/{author}_{receiver}_{timestamp}"

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

def RemoveEmoji(author, receiver, timestamp):
    listener.terminate() # otherwise executing signal-cli below will fail
    subprocess.run(['signal-cli', '--config', CONFIG, 'sendReaction', '-r', '-e', TASK_EMOJI, '-t', timestamp, '-a', author, receiver])





    


# main loop
while True:
    listener = ListenForMessages()
    for line in iter(listener.stdout.readline, ""):
        ProcessPayload(json.loads(line))
    if listener.wait() != 0: # non-zero return code indicates device is not linked
        if not LinkDevice(): # tries for 1min
            time.sleep(4 * 60) # wait 1+4min between repeated link emails
