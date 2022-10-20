FROM node:10-alpine
# ENV PORT 8080
WORKDIR /usr/src/notify/socket
COPY src/. /usr/src/notify/socket

RUN npm install -g nodemon
# RUN npm install -g ws
# RUN npm install -g redis
RUN npm install

ENTRYPOINT ["nodemon", "/usr/src/notify/socket/notify_server.js"]