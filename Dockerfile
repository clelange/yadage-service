FROM fedora:27
RUN dnf install -y gcc gcc-c++ graphviz-devel ImageMagick python-devel libffi-devel openssl openssl-devel unzip nano autoconf automake libtool git python redhat-rpm-config; yum clean all
RUN curl https://bootstrap.pypa.io/get-pip.py | python -
RUN pip install Flask redis msgpack-python python-socketio gevent gevent-websocket requests

#RUN curl --silent --location https://rpm.nodesource.com/setup_6.x | bash -
RUN curl --silent --location https://rpm.nodesource.com/setup_8.x | bash -
RUN dnf install -y nodejs
RUN npm install -g bower;  echo '{ "allow_root": true }' > /root/.bowerrc

RUN pip install Flask https://github.com/sublee/flask-autoindex/archive/e3d449a.zip redis gevent gevent-websocket
ADD . /code
WORKDIR /code
RUN pip install -e .
RUN cd yadageservice; bower install
CMD python yadageservice/app.py
