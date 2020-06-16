import time
import subprocess
import json

SM_ID = "SM02"

# Panels list
panels = ["P01", "P02", "P03", "P04", "P05"]

# They need to start listening to panels' channels
panelsRoots = {
    "P01": "EMBJEGEB9CDFBMHQFBMXAVSJNTQULVUPJYHTIGMXEKRLRMEZPDBPYSOQMSHHMAFZKYQPUULNHVOZSRRRH",
    "P02": "WGVLZDBCMFGCEYA9QRNKVGLA9AZRPUAZAS9OCENFQQGIESVEDVEJNKUQWMOPOTMKTGMM9DAHKYJIVRLWH",
    "P03": "YKDCRHXABZN9NBIHEJCAJUFMGCFUMLIDHQKDBJYURPMRAIGCBCBYVDRMPSIQGRYGHDIS9MBLI9ZPUJEZN",
    "P04": "SZZGWNJ9FRE9UYLSHRNUSUVPDOYAOQRCVAHSDXDWRSXMDUFQLM9VFNJKVKBRRA9XCPAUGGIZCYFXBVLVW",
    "P05": "KCNKHCHJTXOIVAOZBQACKHPYF9EWOCY9QYUAOBHO9DDHOPJTGFTXMSHXRGHVLBPDQNRCOHAPSKLVSGKXZ"
}

# Panel time series (panel_id: timeserie_json)
timeseries = {
    "D01": "timeserie_D01",
    "D02": "timeserie_D02",
    "D03": "timeserie_D03",
    "D04": "timeserie_D04",
    "D05": "timeserie_D05"
}

while True:

    for panel in panels:
        try:
            received_data = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel_receiver.js " +
                                                     panelsRoots[panel]], shell=True)
            output = json.loads(received_data)
            print(output["data"])
            panelsRoots[panel] = output["next_root"]

            if output["data"]["type"] == "SM_REQUEST":

                try:
                    getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/smart_meter.js " +
                                            str(output["data"]["device_id"]) + " " + str(output["data"]["panel_id"]) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                            "PANEL_RESPONSE" + " " + "PANEL"], shell=True)
                    #print(getData)
                    start = start + 1
                except:
                    #print(e.output)
                    print("Error sending RESPONSE transaction")

        except:
            print("No more data")
        time.sleep(5)
