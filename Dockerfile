FROM ubuntu:latest

# install required tools
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		wget tar ca-certificates openjdk-21-jre-headless python3 python3-requests python3-qrcode
# sed jq qrencode curl bash

# # set the correct locale so java supports emojis
# RUN apt-get install -y locales && \
#     sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
#     locale-gen
# ENV LANG en_US.UTF-8
# ENV LANGUAGE en_US:en
# ENV LC_ALL en_US.UTF-8

# install signal-cli
ENV SIGNAL_CLI_VERSION=0.13.12
RUN set -eux; \
    wget https://github.com/AsamK/signal-cli/releases/download/v"${SIGNAL_CLI_VERSION}"/signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz; \
    tar xf signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz -C /opt; \
    ln -sf /opt/signal-cli-"${SIGNAL_CLI_VERSION}"/bin/signal-cli /usr/local/bin/; \
    rm signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz

# copy files
COPY --chmod=500 signal_bot.py /
RUN mkdir /signal_bot_messages
RUN mkdir /signal_bot_config
VOLUME /signal_bot_messages
VOLUME /signal_bot_config

# run (requires environment var GOOGLE_APPS_SCRIPT_URL to be set)
ENTRYPOINT ["python3", "-i"]
