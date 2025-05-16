# FROM node:10-alpine
FROM node:24-alpine
# ENV PORT 8080
WORKDIR /usr/src/notify/socket
COPY src/. /usr/src/notify/socket

#Turns off ssl
RUN npm set strict-ssl false
RUN npm install -g nodemon
# RUN npm install -g ws
# RUN npm install -g redis
RUN npm install
RUN npm set strict-ssl true
ENTRYPOINT ["nodemon", "/usr/src/notify/socket/notify_server.js"]