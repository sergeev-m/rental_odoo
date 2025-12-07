FROM odoo:19

USER root

RUN apt-get update; apt-get install -y locales;\
    mkdir -p /usr/share/man/man1; \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/odoo

ADD requirements.txt /home/odoo/

RUN pip3 install -r /home/odoo/requirements.txt --break-system-packages

COPY pre-entrypoint.sh /pre-entrypoint.sh

RUN chmod +x /pre-entrypoint.sh

USER odoo

ENV SHELL=/bin/bash

ENTRYPOINT ["/pre-entrypoint.sh"]

CMD ["odoo"]
