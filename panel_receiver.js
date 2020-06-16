const Mam = require('./lib/mam.client.js');
const IOTA = require('iota.lib.js');
const iota = new IOTA({ provider: 'http://192.168.1.34:14265' });

const MODE = 'restricted'; // public, private or restricted
const SIDEKEY = 'AOBDOCCDWZWMDPPGMSU9TTAQBMDL99XUNLWIVLRNOQLHJRZJMRPHKGUQJHDGXISUXFVCKGNDZCLEXV9CA';

let root;
let key;

// Check the arguments
const args = process.argv;
if(args.length < 3)
{
    console.log('Missing root as argument: node mam_receive.js <root>');
    process.exit();
}
else if(!iota.valid.isAddress(args[2]))
{
    console.log('You have entered an invalid root!');
    process.exit();
}
else
{
    root = args[2];
}

// Initialise MAM State
let mamState = Mam.init(iota);

// Set channel mode
if (MODE == 'restricted')
{
    key = iota.utils.toTrytes(SIDEKEY);
    mamState = Mam.changeMode(mamState, MODE, key);
}
else
{
    mamState = Mam.changeMode(mamState, MODE);
}

async function getData()
{
    let resp = await Mam.fetchSingle(root, MODE, key);
    var json = JSON.parse(iota.utils.fromTrytes(resp.payload));
    root = resp.nextRoot
    var output = {"data": json, "next_root": root}
    console.log(JSON.stringify(output));
}

getData()