const Mam = require('./lib/mam.client.js');
const IOTA = require('iota.lib.js');
const moment = require('moment');
const iota = new IOTA({ provider: 'http://192.168.1.34:14265' });

//IOTA constants
const SEED = '9VPJ9BNMWREYLEBEPLQDZXSUAFBGXBOORMBNRNJ9YFKKCCZZAONPFW9HJYRIPE9YBFIZTLWPPH9GGDDOU'
const MODE = 'restricted'; // public, private or restricted
const SIDEKEY = 'AOBDOCCDWZWMDPPGMSU9TTAQBMDL99XUNLWIVLRNOQLHJRZJMRPHKGUQJHDGXISUXFVCKGNDZCLEXV9CA'
const SECURITYLEVEL = 2; // 1, 2 or 3
let key;

var start = 0;
var cycle = 0;
var earliest_start = 0;
var latest_start = 0;
var working_time = 0;
var device_id = '';
var panel_id = '';
var type = '';
var start_time = 0;
var end_time = 0;
var device_type = '';
var house = '';

// Check the arguments
const args = process.argv;
if(args.length < 11)
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
    start_time = parseInt(args[7])
    end_time = parseInt(args[8])
    device_type = args[9]
    house = args[10]
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
async function createRequestTransaction(device_id, panel_id, cycle, earliest_start, latest_start, working_time, power)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "REQUEST",
        "power": power,
        "timestamp": dateTime,
        "earliest_start": earliest_start,
        "latest_start": latest_start,
        "working_time": working_time,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// Finish transaction
async function createFinishTransaction(device_id, panel_id, cycle)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "FINISH",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// Respnse ACK transaction
async function createResponseAckTransaction(device_id, panel_id, cycle, type)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": type,
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// INIT transaction
async function createInitTransaction(device_id, panel_id, cycle)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "DEVICE_INIT",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// INIT transaction
async function createRevokeTransaction(device_id, panel_id, cycle, type)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": type,
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// Smart meter request transaction (in this case earliest_start and latest_start are used as start_time and end_time to get panel timeserie
async function createSM_requestTransaction(device_id, panel_id, cycle, start_time, end_time)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "SM_REQUEST",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "start_time": start_time,
        "end_time": end_time,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

var mysql = require('mysql')
var con = mysql.createConnection({
  host: "services.pep.it",
  user: "giuseppe",
  password: "google7.11",
  database: "smart_grid"
});

con.connect(function(err) {
  if (err) throw err;

  con.query("SELECT * FROM Timeseries WHERE (Cycle_ID = " + cycle + " AND Device_Type = '" + device_type + "' AND House = '" + house + "')", function (err, result, fields) {
    if (err) throw err;
    //console.log(result[0]);
    cycle = result[0]["Cycle_ID"];
    earliest_start = result[0]["Earliest_Start"]
    latest_start = result[0]["Latest_Start"]
    working_time = result[0]["Working_Time"]
    con.query("SELECT * FROM Power WHERE (Cycle_ID = " + cycle + " AND Device_Type = '" + device_type + "' AND House = '" + house + "')", function (err, result, fields) {
          if (err) throw err;
          //console.log(result[0]);

          if(type == "REQUEST") createRequestTransaction(device_id, panel_id, cycle, earliest_start, latest_start, working_time, JSON.stringify(result));
          else if(type == "FINISH") createFinishTransaction(device_id, panel_id, cycle);
          else if(type == "ACCEPT" || type == "DENY") createResponseAckTransaction(device_id, panel_id, cycle, type);
          else if(type == "SM_REQUEST") createSM_requestTransaction(device_id, panel_id, cycle);
          else if(type == "INIT") createInitTransaction(device_id, panel_id, cycle)
          else if(type == "REVOKE_ACCEPT" || type == "REVOKE_DENY") createRevokeTransaction(device_id, panel_id, cycle, type)

          con.end();
        });
  });
});
