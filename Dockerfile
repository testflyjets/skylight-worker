FROM 271573709197.dkr.ecr.us-east-1.amazonaws.com/fedora-gui:latest

RUN dnf install -y \
    python3-tkinter \
    python3-devel \
    xxd \
    scrot \
    xauth && \
    dnf clean all


RUN mkdir /app
COPY requirements.txt /app
RUN pip install --upgrade pip
RUN pip install --upgrade --force-reinstall --ignore-installed setuptools packaging
ENV PATH "PATH=$PATH:/usr/bin/"
WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

RUN mkdir -p /var/tmp/cache/
RUN mkdir /tmp/downloads/
RUN chmod 700 -R /tmp/downloads/
COPY ./display.sh /app/display.sh
RUN chmod +x /app/display.sh
COPY ./supervisor/ /app/supervisor/

CMD ["supervisord", "-c", "/app/supervisor/supervisord.conf"]