FROM ubuntu:latest

# install required tools
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		sed jq qrencode wget curl tar bash

# install java 21
ENV JAVA_INSTALLER=jdk-21_linux-x64_bin.deb
RUN set -eux; \
    wget https://download.oracle.com/java/21/latest/${JAVA_INSTALLER} --no-check-certificate; \
    apt-get install -y ./${JAVA_INSTALLER}; \
    rm ${JAVA_INSTALLER}

# install signal-cli
ENV SIGNAL_CLI_VERSION=0.12.8
RUN set -eux; \
    wget https://github.com/AsamK/signal-cli/releases/download/v"${SIGNAL_CLI_VERSION}"/signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz --no-check-certificate; \
    tar xf signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz -C /opt; \
    ln -sf /opt/signal-cli-"${SIGNAL_CLI_VERSION}"/bin/signal-cli /usr/local/bin/; \
    rm signal-cli-"${SIGNAL_CLI_VERSION}".tar.gz

# copy files
COPY --chmod=500 signal_bot.sh /
RUN mkdir /signal_bot_messages
RUN mkdir /signal_bot_config
VOLUME /signal_bot_messages
VOLUME /signal_bot_config

# run
ENTRYPOINT ["/signal_bot.sh"] # requires environment var GOOGLE_APPS_SCRIPT_URL to be set
