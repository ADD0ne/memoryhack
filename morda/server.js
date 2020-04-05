const express = require('express');
const app = express();
const server = require('http').createServer(app);
const io = require('socket.io').listen(server);
const MongoClient = require("mongodb").MongoClient;
server.listen(8485);

app.use(express.static('src'));

app.get('/', function (request, respons) {
    respons.sendFile(__dirname + "/index.html");
});

var data_photo;


const url = "mongodb://localhost:27017/";
const mongoClient = new MongoClient(url, { useNewUrlParser: true });
 
mongoClient.connect(function(err, client){
    
    const db = client.db("vk");
    const collection = db.collection("photo");
    collection.find().toArray(function(err, results){
        data_photo = results;
        client.close();
    });
});


var connections = [];
io.sockets.on('connection', function (socket) {
    connections.push(socket);
    console.log("user - connect"); 
    
    socket.on('disconnect', function (data) {
        connections.splice(connections.indexOf(socket), 1);
    });

    socket.on("get_photo", function(number){
        try {
            
            respons = data_photo[number];
            
            socket.emit("respons_photo", {
                "status" : 200,
                "data" : respons,
                "len_data" : data_photo.length,
            });
        } catch (error) {
            console.log(error);
            socket.emit("respons_photo", { 
                "status" : "500",
                "data" : null,
                "len_data" : null,
            });
        }
    });


    socket.on('del_photo', (photo_id) => {
        // to do
    });

});

