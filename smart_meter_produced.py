import time
import subprocess
import json

SM_ID = "SM01"

# Devices list (included smart meter)
devices = ["D01", "D02", "D03", "D04", "D05"]

# They need to start listening to devices' channels
devicesRoots = {
    "D01": "XVOTTBFLHSQCGPUWVHGIKYRBDIGPWFQVI9QBQTIYRCJWSLAUVNSSD9LSK9LKGROEGPNWSDVT9SPVF9WKR",
    "D02": "WGVLZDBCMFGCEYA9QRNKVGLA9AZRPUAZAS9OCENFQQGIESVEDVEJNKUQWMOPOTMKTGMM9DAHKYJIVRLWH",
    "D03": "YKDCRHXABZN9NBIHEJCAJUFMGCFUMLIDHQKDBJYURPMRAIGCBCBYVDRMPSIQGRYGHDIS9MBLI9ZPUJEZN",
    "D04": "WGVLZDBCMFGCEYA9QRNKVGLA9AZRPUAZAS9OCENFQQGIESVEDVEJNKUQWMOPOTMKTGMM9DAHKYJIVRLWH",
    "D05": "KCNKHCHJTXOIVAOZBQACKHPYF9EWOCY9QYUAOBHO9DDHOPJTGFTXMSHXRGHVLBPDQNRCOHAPSKLVSGKXZ",
}

# Panel time series (panel_id: timeserie_json)
timeseries = {
    "P01": "timeserie_P01",
    "P02": "timeserie_P02",
    "P03": "timeserie_P03",
    "P04": "timeserie_P04",
    "P05": "timeserie_P05"
}

while True:

    for device in devices:
        try:
            received_data = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel_receiver.js " +
                                                     devicesRoots[device]], shell=True)
            output = json.loads(received_data)
            print(output["data"])
            devicesRoots[device] = output["next_root"]

            if output["data"]["type"] == "SM_REQUEST":
		
		# Send transaction
                try:
                    getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/smart_meter.js " +
                                            str(output["data"]["device_id"]) + " " + str(output["data"]["panel_id"]) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                            "DEVICE_RESPONSE" + " " + "DEVICE"], shell=True)
                    #print(getData)
                    start = start + 1
                except:
                    #print(e.output)
                    print("Error sending RESPONSE transaction")

        except:
            print("No more data")
        time.sleep(5)
