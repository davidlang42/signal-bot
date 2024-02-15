#!/usr/bin/bash

set -eu

if [ -z "${GOOGLE_APPS_SCRIPT_URL}" ]; then
    echo "Must set environment variable GOOGLE_APPS_SCRIPT_URL"
    exit 1 # failed
fi

set -x

TASK_EMOJI="☑️"
MESSAGES="/signal_bot_messages"
CONFIG="/signal_bot_config"

set -o pipefail # link_device, read_messages

send_email() { # subject html
    curl -G "$GOOGLE_APPS_SCRIPT_URL" --data-urlencode "action=email" --data-urlencode "title=$1" --data-urlencode "html=$2"
}

add_task() { # title notes
    local due=$(date -d "$DATE_ADJUSTMENT" +%Y-%m-%d)
    curl -G "$GOOGLE_APPS_SCRIPT_URL" --data-urlencode "action=task" --data-urlencode "due=$due" --data-urlencode "title=$1" --data-urlencode "notes=$2"
}

send_link_email() {
    local link
    read -r link
    local png=$(qrencode -o - "$link" | base64 -w 0)
    local html="<p>$link</p><img src=\"data:image/png;base64,$png\" />"
    if ! send_email "SignalBot is not linked" "$html"
    then
        echo Failed to send email
        exit 1
    fi
    local rest=$(cat)
}

link_device() {
    # set -o pipefail
    signal-cli --config "$CONFIG" link -n "SignalBot" | send_link_email
}

read_messages() {
    # set -o pipefail
    sh -c "echo \$\$; exec signal-cli --config \"$CONFIG\" -o json receive -t -1 --ignore-attachments --ignore-stories" | process_messages
    result=$?
    if [[ $result -eq 143 ]]
    then
        # correctly terminated by process_messages
        return 0
    else
        return $result
    fi
}

process_messages() {
    local pid
    read -r pid
    local line
    while read -r line
    do
        local source="$(jq -r .envelope.source <<< "$line")"
        local sent
        if sent="$(jq -e .envelope.syncMessage.sentMessage <<< "$line")"
        then
            # I sent a message or I reacted
            local destination="$(jq -r .destination <<< "$sent")"
            check_for_content "$sent" "$source" "$destination" "to $destination"
            check_for_reaction "$pid" "$sent" "$source" "$destination"
        fi
        local received
        if received="$(jq -e .envelope.dataMessage <<< "$line")"
        then
            # they sent a messsage or they reacted (but ignore their reactions)
            local my_account="$(jq -r .account <<< "$line")"
            local source_name="$(jq -r .envelope.sourceName <<< "$line")"
            check_for_content "$received" "$source" "$my_account" "from $source_name"
        fi
    done
}

check_for_content() { # msg_json source destination from_to_display_name
    local message
    if message="$(jq -e -r .message <<< "$1")"
    then
        local timestamp="$(jq -r .timestamp <<< "$1")"
        store_message "$message" "$2" "$3" "$timestamp" "$4"
        local reply
        if reply="$(jq -e .quote <<< "$1")"
        then
            local reply_to_author="$(jq -r .author <<< "$reply")"
            local reply_to_timestamp="$(jq -r .id <<< "$reply")"
            local reply_to_receiver="$3"
            if [ "$reply_to_author" = "$reply_to_receiver" ]
            then
                reply_to_receiver="$2"
            fi
            local previous_message="$(read_message "$reply_to_author" "$reply_to_receiver" "$reply_to_timestamp")"
            append_message "$previous_message" "$2" "$3" "$timestamp"
        fi
    fi
}

check_for_reaction() { # pid msg_json source destination
    local emoji="$(jq -r .reaction.emoji <<< "$2")"
    local remove="$(jq -r .reaction.isRemove <<< "$2")"
    if [ "$emoji" = "$TASK_EMOJI" ] && [ "$remove" = "false" ]
    then
        local author="$(jq -r .reaction.targetAuthor <<< "$2")"
        local timestamp="$(jq -r .reaction.targetSentTimestamp <<< "$2")"
        if [ "$author" = "$4" ]
        then
            handle_reaction "$1" "$author" "$3" "$timestamp"
        else
            handle_reaction "$1" "$author" "$4" "$timestamp"
        fi
    fi
}

store_message() { # message msg_author msg_receiver msg_timestamp from_to_display_name
    echo "$1" > "$(message_path "$2" "$3" "$4")"
    echo "(Signal message $5)" >> "$(message_path "$2" "$3" "$4")"
}

append_message() { # message msg_author msg_receiver msg_timestamp
    echo "$1" >> "$(message_path "$2" "$3" "$4")"
}

read_message() { # msg_author msg_receiver msg_timestamp
    cat "$(message_path "$1" "$2" "$3")"
}

message_path() { # msg_author msg_receiver msg_timestamp
    echo "$MESSAGES/${1}_${2}_${3}"
}

handle_reaction() { # pid msg_author msg_receiver msg_timestamp
    kill "$1" # so that we can use remove_emoji below
    local name="$(read_message "$2" "$3" "$4" | head -n1)"
    local notes="$(read_message "$2" "$3" "$4" | sed 1d)"
    if [[ -z "$name" ]]
    then
        name="Unknown Task"
        notes="Signal message from $2 to $3 at $4 could not be found"
    fi
    if ! add_task "$name" "$notes"
    then
        echo Failed to add task: "$name"
        exit 1
    fi
    if ! remove_emoji "$2" "$3" "$4"
    then
        echo Failed to remove emoji: "$2" "$3" "$4"
        exit 1
    fi
}

remove_emoji() { # msg_author msg_receiver msg_timestamp
    log_and_run signal-cli -v --config "$CONFIG" sendReaction -r -e ☑️ -t "$3" -a "$1" "$2"
}

log_and_run() {
  echo "$@" > "$MESSAGES/last_remove_emoji"
  "$@"
}

# main loop
while true
do
    if ! read_messages # blocks until an emoji gets processed
    then
        if ! link_device # tries for 1min
        then
            sleep 240 # wait 1+4min between repeated link emails
        fi
    fi
done
