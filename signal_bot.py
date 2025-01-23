#!/usr/bin/python
import os
import io
import base64
import subprocess
import json
import time
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
    #TODO: local due=$(date -d "$DATE_ADJUSTMENT" +%Y-%m-%d)
    response = requests.get(appsScriptUrl, {
        'action':'task',
        'due': due,
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
    html = f"<p>{link}</p><img src='data:image/png;base64,{base64string}' />"
    if not SendEmail("SignalBot is not linked", html):
        print("Failed to send link email")
        process.terminate()
        return False
    returncode = process.wait()
    return returncode == 0

def WaitForMessage(): #TODO: formerly read_messages
    #TODO: could try
    # popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    # for stdout_line in iter(popen.stdout.readline, ""):
    #     yield stdout_line 
    # popen.stdout.close()
    # return_code = popen.wait()
    #TODO: previously tried to process messages continuously until actually nessesary to terminate it, now just reads 1 at a time (will need to test if this is performant)
    result = subprocess.run(['signal-cli', '--config', CONFIG, '-o', 'json', 'receive', '-t', '-1', '--ignore-attachments', '--ignore-stories', '--max-messages', '1'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        return False
    msg = json.loads(result.stdout.decode())
    ProcessMessage(msg)
    return True

def ProcessMessage(m):
    source = m["envelope"]["source"]
    sent = m["envelope"]["syncMessage"]["sentMessage"]
    if sent:
        # I sent a message or I reacted
        dest = sent["destination"]
        #TODO: check_for_content "$sent" "$source" "$destination" "to $destination"
        #TODO: check_for_reaction "$pid" "$sent" "$source" "$destination"
    received = m["envelope"]["dataMessage"]
    if received:
        # they sent a messsage or they reacted (but ignore their reactions)
        my_account = m["account"]
        source_name = m["envelope"]["sourceName"]
        #TODO: check_for_content "$received" "$source" "$my_account" "from $source_name"

def CheckForContent(o, source, dest, from_to_display_name):
    message = o["message"]
    if not message:
        return False
    timestamp = o["timestamp"]
    StoreMessage(message, source, dest, timestamp, from_to_display_name)
    reply = o["quote"]
    if reply:
        reply_to_author = reply["author"]
        reply_to_timestamp = reply["id"]
        reply_to_receiver = dest
        if reply_to_author == reply_to_receiver:
            reply_to_receiver = source
        previous_message = ReadMessage(reply_to_author, reply_to_receiver, reply_to_timestamp)
        AppendMessage(previous_message, source, dest, timestamp)

def CheckForReaction(o, source, dest):
    emoji = o["reaction"]["emoji"]
    remove = o["reaction"]["isRemove"].strip().lower() == "true"
    if emoji == TASK_EMOJI and not remove:
        author = o["reaction"]["targetAuthor"]
        timestamp = o["reaction"]["targetSentTimestamp"]
        if author == dest:
            HandleReaction(author, source, timestamp)
        else:
            HandleReaction(author, dest, timestamp)

def StoreMessage(message, author, receiver, timestamp, from_to_display_name):
    print(message)
    #TODO: echo "$1" > "$(message_path "$2" "$3" "$4")"
    #TODO: echo "(Signal message $5)" >> "$(message_path "$2" "$3" "$4")"

def AppendMessage(message, author, receiver, timestamp):
    print(message)
    #TODO: echo "$1" >> "$(message_path "$2" "$3" "$4")"

def ReadMessage(author, receiver, timestamp):
    print("read message")
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
    subprocess.run(['signal-cli', '--config', CONFIG, 'sendReaction', '-r', '-e', TASK_EMOJI, '-t', timestamp, '-a', author, receiver])

# main loop
while True:
    if not WaitForMessage(): # blocks until a message arrives
        if not LinkDevice(): # tries for 1min
            time.sleep(240) # wait 1+4min between repeated link emails
