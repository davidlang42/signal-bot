FROM ubuntu:latest

# install required tools
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		sed head jq base64 qrencode wget curl tar bash

# install signal-cli
ENV SIGNAL_CLI_VERSION=0.12.7
RUN set -eux; \
    wget https://github.com/AsamK/signal-cli/releases/download/v"${SIGNAL_CLI_VERSION}"/signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz; \
    tar xf signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz -C /opt; \
    ln -sf /opt/signal-cli-"${SIGNAL_CLI_VERSION}"/bin/signal-cli /usr/local/bin/; \
    rm signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz

# copy files
COPY --chmod=500 signal_bot.sh /
RUN mkdir /signal_bot_messages

# run
ENTRYPOINT ["/signal_bot.sh"] # requires environment var GOOGLE_APPS_SCRIPT_URL to be set
