const Mam = require('./lib/mam.client.js');
const IOTA = require('iota.lib.js');
const moment = require('moment');
const iota = new IOTA({ provider: 'http://192.168.1.34:14265' });

//IOTA constants
const SEED = 'OOE9NIVELMOTBTKSEAHBSQYFGYLDLKWECERYIFNKDJSMAGXLZWHIQIQNQFTDAHTIDYXDSTISWHJPUXBPD'
const MODE = 'restricted'; // public, private or restricted
const SIDEKEY = 'AOBDOCCDWZWMDPPGMSU9TTAQBMDL99XUNLWIVLRNOQLHJRZJMRPHKGUQJHDGXISUXFVCKGNDZCLEXV9CA'
const SECURITYLEVEL = 2; // 1, 2 or 3
let key;

var start = 0;
var cycle = 0;
var device_id = '';
var panel_id = '';
var type = ''; //DEVICE/PANEL

// Check the arguments
const args = process.argv;
if(args.length < 8)
{
    console.log('Missing parameters');
    process.exit();
}
else
{
    device_id = args[2];
    panel_id = args[3];
    cycle = parseInt(args[4]);
    start = parseInt(args[5]);
    type = args[6];
    sender = args[7];
}

// Initialise MAM State
let mamState = Mam.init(iota, SEED, SECURITYLEVEL, start);

// Set channel mode
if(MODE == 'restricted')
{
    const key = iota.utils.toTrytes(SIDEKEY);
    mamState = Mam.changeMode(mamState, MODE, key);
}
else
{
    mamState = Mam.changeMode(mamState, MODE);
}

// This function allow you to create an IOTA transaction passing json data (packet).
// It will return the message root
const publish = async function(packet) {
    // Create MAM Payload
    const trytes = iota.utils.toTrytes(JSON.stringify(packet));
    const message = Mam.create(mamState, trytes);

    // Save new mamState
    mamState = message.state;
    console.log('Root: ', message.root);
    //console.log('Address: ', message.address);

    // Attach the payload.
    await Mam.attach(message.payload, message.address, 3, 9, 'REQUEST');

    return message.root;
}

// This function allow you to publish a transaction created with the previous function
async function createResponseTransaction(type, device_id, panel_id, cycle, power)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": type,
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "power": power,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

var mysql = require('mysql')
var con = mysql.createConnection({
  host: "raspberry3b.pep.it",
  user: "giuseppe",
  password: "google7.11",
  database: "smart_meter"
});

con.connect(function(err) {
    if (err) throw err;
    table = '';
    id = '';
    id_column = '';
    if(sender == "DEVICE")
    {
        table = "PanelProduction";
        id = device_id;
        id_column = 'Panel_ID'
    }
    else if(sender == "PANEL")
    {
        table = "DeviceConsumption";
        id = panel_id;
        id_column = 'Device_ID';
    }
    con.query("SELECT * FROM " + table + " WHERE " + id_column + " = " + id, function (err, result, fields) {
    if (err) throw err;
    //console.log(result[0]);
    if(type == "DEVICE_RESPONSE" || type == "PANEL_RESPONSE") createResponseTransaction(type, device_id, panel_id, cycle, JSON.stringify(result));
    con.end();

    });
});
