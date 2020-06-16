const Mam = require('./lib/mam.client.js');
const IOTA = require('iota.lib.js');
const moment = require('moment');
const iota = new IOTA({ provider: 'http://192.168.1.34:14265' });

//IOTA constants
const SEED = 'WFTMNJTHQAJHQDEITGXKAITJUX9YNXDSUIQS9NTXKYSJGEHSBXNWRGZEHHCLTXK9BAEKE9RKHSDOS9PZS'
const MODE = 'restricted'; // public, private or restricted
const SIDEKEY = 'AOBDOCCDWZWMDPPGMSU9TTAQBMDL99XUNLWIVLRNOQLHJRZJMRPHKGUQJHDGXISUXFVCKGNDZCLEXV9CA'
const SECURITYLEVEL = 2; // 1, 2 or 3
let key;

var start = 0;
var cycle = 0;
var device_id = '';
var panel_id = '';
var type = '';
var score = 0.0;
var starting_time = 0;

// Check the arguments
const args = process.argv;
if(args.length < 9)
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
    score = parseFloat(args[7]);
    starting_time = parseInt(args[8]);
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
async function createResponseTransaction(device_id, panel_id, cycle, score, starting_time)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "PROPOSAL",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle,
        "score": score,
        "starting_time": starting_time
    };
    const root = await publish(json);
    console.log(json);
}

// Revoke transaction
async function createRevokeTransaction(device_id, panel_id, cycle)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "REVOKE",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// INIT transaction
async function createInitTransaction(device_id, panel_id, cycle, type)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "PANEL_INIT",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

// Smart meter request transaction (in this case score and starting_time are used as start_time and end_time to get device timeserie
async function createSM_requestTransaction(device_id, panel_id, cycle, score, starting_time)
{
    const dateTime = moment().utc().format('DD/MM/YYYY hh:mm:ss');

    //send transaction
    var json =
    {
        "type": "SM_REQUEST",
        "timestamp": dateTime,
        "device_id": device_id,
        "panel_id": panel_id,
        "start_time": score,
        "end_time": starting_time,
        "request_id": cycle
    };
    const root = await publish(json);
    console.log(json);
}

var BUSY_POWER = [
  {
    id_device: "ID01",
    busy_power: 2000,
    start_time: 3*3600,
    end_time: 4.5*3600
  },
  {
    id_device: "ID02",
    busy_power: 3000,
    start_time: 7*3600,
    end_time: 8*3600
  },
  {
    id_device: "ID03",
    busy_power: 2500,
    start_time: 9.5*3600,
    end_time: 11*3600
  },
];

if(type == "PROPOSAL") createResponseTransaction(device_id, panel_id, cycle, score, starting_time);
else if(type == "REVOKE") createRevokeTransaction(device_id, panel_id, cycle)
else if(type == "SM_REQUEST") createSM_requestTransaction(device_id, panel_id, cycle)
else if(type == "INIT") createInitTransaction(device_id, panel_id, cycle)
