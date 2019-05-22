FROM python
MAINTAINER sadisticsolutione@gmail.com

ENV REPLICATOR_CONFIG_SHEET=""

COPY . /script
RUN cd /script && \
    pip install -r requirements.txt

WORKDIR /script
CMD tail -f /dev/null
# ENTRYPOINT ./entrypoint.sh
