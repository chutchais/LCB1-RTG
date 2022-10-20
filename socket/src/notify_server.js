const WebSocket = require('ws');
const redis = require('redis');

// Configuration: adapt to your environment
const REDIS_SERVER = "redis://redis:6379/0";
const WEB_SOCKET_PORT = 3000;

// Create & Start the WebSocket server
const server = new WebSocket.Server({ port : WEB_SOCKET_PORT });

var subscriber = redis.createClient(REDIS_SERVER);

server.on('connection', function connection(ws) {
    console.log('connection')
    subscriber.on("message", function (channel, message) {
        console.log("Message: " + message + " on channel: " + channel + " is arrive!");
        ws.send(message);
    });
    ws.send('{}')
});

subscriber.subscribe("RTG-NOTIFY");