import time
import subprocess
import json
from datetime import datetime

#device parameters
device_type = 'dishwasher'
house = 'kn04'
DEVICE_ID = 'D01'
state = 0 #0 = device OFF, 1 = device ON. It simiulates a sort of readState() function
previous_state = 0
FINISH = 0 # change to 1 when cycle is finished

# This variable contains the chosen panel, based on 50% on its reputation and 50% based on its score
# (panel score is the sum of these 2 values divided by 2)
chosen = {
  "panel_id": "P01",
  "panel_score": 0,
  "start_time": 0,
}
i = 0
# Index of the row corresponding to the current cycle
cycle = 0
# transaction index
start = 1

# Panels list
panels = ["P01", "P02", "P03", "P04", "P05", "SM01"]

# They need to start listening to panels' channels
panelsRoots = {
    "P01": "NCDGXPLVUPDXRJRNRKKBXIARSOAELRVMR9KRDEVPWNUSRKWMVZBDCLWCESUHYRDYFRQZ9ZTOHMCFHMIRD",
    "P02": "WGVLZDBCMFGCEYA9QRNKVGLA9AZRPUAZAS9OCENFQQGIESVEDVEJNKUQWMOPOTMKTGMM9DAHKYJIVRLWH",
    "P03": "YKDCRHXABZN9NBIHEJCAJUFMGCFUMLIDHQKDBJYURPMRAIGCBCBYVDRMPSIQGRYGHDIS9MBLI9ZPUJEZN",
    "P04": "SATIRVGWQTVOCFJJSIVQIKXTPUVWYQNSXAEY9KJGRKJ9KDKBLXEPMEUJTCSRKEEINEHMXHRORDLRRWQPQ",
    "P05": "KCNKHCHJTXOIVAOZBQACKHPYF9EWOCY9QYUAOBHO9DDHOPJTGFTXMSHXRGHVLBPDQNRCOHAPSKLVSGKXZ",
    "SM01": "WSPFIWRDHBYSSLEOANFHNHOPVEUACGTNXPZPHZNWYVXXWMOWKGWGV9EDVUDKMLCQBTSNTRPTPDKJXLOTJ"
}

#panels reputations (panel_id: reputation_value)
panelsReputations = {
       "P01": 0.0,
       "P02": 0.0,
       "P03": 0.0,
       "P04": 0.0,
       "P05": 0.0
}

# Value is in the interval [0, 1], where 0 is the worst case, 1 the best one
def calculatePanelReputation(estimated_timeserie, real_timeserie):
    # Take only samples of real timeserie corresponding with samples of estimated timeserie
    # (to evaluate two functions with same number of element

    # This has the same length of estimated timeserie.
    reduced_real_timeserie = []

    for element in estimated_timeserie:
        for real_element in real_timeserie:
            if (real_element["Time"] == element["Time"]):
                reduced_real_timeserie.append(real_element)
                break

    area_minimum = 0
    area_difference = 0

    for i in range(0, len(estimated_timeserie) - 1):
        # Functions keep order relation in the current and next sample
        if ((estimated_timeserie[i]["Power"] > reduced_real_timeserie[i]["Power"]) and (
                estimated_timeserie[i + 1]["Power"] > reduced_real_timeserie[i + 1]["Power"])):
            area_minimum = area_minimum + (
                        reduced_real_timeserie[i]["Power"] + reduced_real_timeserie[i + 1]["Power"]) / 2
            area_difference = area_difference + abs(
                (estimated_timeserie[i]["Power"] + estimated_timeserie[i + 1]["Power"] -
                 reduced_real_timeserie[i]["Power"] - reduced_real_timeserie[i]["Power"])) / 2

        elif ((estimated_timeserie[i]["Power"] < reduced_real_timeserie[i]["Power"]) and (
                estimated_timeserie[i + 1]["Power"] < reduced_real_timeserie[i + 1]["Power"])):
            area_minimum = area_minimum + (estimated_timeserie[i]["Power"] + estimated_timeserie[i + 1]["Power"]) / 2
            area_difference = area_difference + abs(
                (estimated_timeserie[i]["Power"] + estimated_timeserie[i + 1]["Power"] -
                 reduced_real_timeserie[i]["Power"] - reduced_real_timeserie[i]["Power"])) / 2

        # Functions don't keep order relation in the current and next sample (in example, f1(t1) > f2(t1) but f1(t2) < f2(t2)).
        # In this case, we calculate the intersect between two segments and calculate area of two triangles that they generate
        else:
            # Straight line params (e = estimated, r = real)
            m_e = float(estimated_timeserie[i + 1]["Power"] - estimated_timeserie[i]["Power"])
            q_e = estimated_timeserie[i]["Power"] - m_e

            m_r = float(reduced_real_timeserie[i + 1]["Power"] - reduced_real_timeserie[i]["Power"])
            q_r = reduced_real_timeserie[i]["Power"] - m_r

            if m_e == m_r:
                m_e = m_e + 0.01
            intersect = (q_r - q_e) / (m_e - m_r) - 1

            # Sum of 2 triangles
            area_difference = area_difference + abs(estimated_timeserie[i]["Power"] - reduced_real_timeserie[i]["Power"]) * intersect / 2 + \
                              abs(estimated_timeserie[i + 1]["Power"] - reduced_real_timeserie[i + 1]["Power"]) * (1 - intersect) / 2

            # Difference between the trapeze with one base equals to the smallest i-th sample and the triangle with base equal to the difference between (i + 1)-th samples
            if estimated_timeserie[i]["Power"] < reduced_real_timeserie[i]["Power"]:
                area_minimum = area_minimum + (estimated_timeserie[i]["Power"] + estimated_timeserie[i + 1]["Power"]) / 2 - \
                               abs(estimated_timeserie[i + 1]["Power"] - reduced_real_timeserie[i + 1]["Power"]) * (1 - intersect) / 2
            else:
                area_minimum = area_minimum + (reduced_real_timeserie[i]["Power"] + reduced_real_timeserie[i + 1]["Power"]) / 2 - \
                               abs(estimated_timeserie[i + 1]["Power"] - reduced_real_timeserie[i + 1]["Power"]) * (1 - intersect) / 2
        # print("Area minimum = " + str(area_minimum))
        # print("Area difference = " + str(area_difference))
    return area_difference / (area_difference + area_minimum)

# This function simultate read of a GPIO pin
def readState():
    return 0

# This function is used to retrieve data from a panel; it needs a panel ID
def getData(panel):
    try:
        received_data = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel_receiver.js " +
                                                panelsRoots[panel]], shell=True)
        output = json.loads(received_data)
        print(output["data"])
        panelsRoots[panel] = output["next_root"]
        return output["data"]
    except:
        print("Exception")
        return None

# This function find the panel with best score
def findBestPanel(start, panelList):

    for panel in panelList:

        # To avoid device stuck on specific panel if it doesn't reply, each panel has to send its PROPOSAL in 30 seconds
        timeout = 30

        # Send REQUEST to next panel
        try:
            print("Sending REQUEST transaction to panel " + panel + "...")
            print(start)
            output = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " +
                                     DEVICE_ID + " " + panel + " " + str(cycle) + " " + str(start) + " " + "REQUEST" + " " + str(0) + " "
                                              + str(0) + " " + device_type + " " + house], shell=True)

            #deviceTimeserie = output["data"]["power"]
            print("REQUEST transaction sent")
            start = start + 1
        except:
            print("Error sending REQUEST transaction")

        # check timeout
        while timeout > 0:
            data = getData(panel)
            if data is not None:

                if data["device_id"] == DEVICE_ID and data["type"] == "PROPOSAL":
                    print("The socre of the panel " + data["panel_id"] + " is " + str(data["score"]))

                    # average between panel score and its reputation
                    if float((data["score"] + panelsReputations[data["panel_id"]]) / 2) > float((chosen["panel_score"] + panelsReputations[data["panel_id"]]) / 2):
                        chosen["panel_id"] = data["panel_id"]
                        chosen["panel_score"] = data["score"]
                        chosen["start_time"] = data["starting_time"]
                        timeout = 0
            else:
                print("No data received")
                timeout = timeout - 1
            time.sleep(2)

    # When there arent't more panels to query, send ACCEPT to best panel (chosen), DENY to other
    for panel in panelList:
        if panel == chosen["panel_id"]:
            try:
                print("Best panel is " + chosen["panel_id"] + ", with a score of " + str(chosen["panel_score"]))
                print("Sending ACCEPT transaction to panel " + panel + "...")
                subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " +
                     DEVICE_ID + " " + chosen["panel_id"] + " " + str(cycle) + " " + str(start) + " " + "ACCEPT" + " " + str(0) + " " + str(0) + " " + device_type + " " + house], shell=True)
                print("ACCEPT transaction sent")
                start = start + 1
            except:
                print("Error sending ACCEPT transaction")
        else:
            try:
                print("Sending DENY transaction to panel " + panel + "...")
                subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " +
                     DEVICE_ID + " " + chosen["panel_id"] + " " + str(cycle) + " " + str(start) + " " + "DENY" + " " + str(0) + " " + str(0) + " " + device_type + " " + house], shell=True)
                print("DENY transaction sent")
                start = start + 1
            except:
                print("Error sending DENY transaction")


# START
# Choose best panel
findBestPanel(start, panels)

while FINISH != 1:

    previous_state = state

    # Get state of device
    state = readState()

    # If device is turned off, so its state changes from 1 to 0
    if(previous_state == 1 and state == 0):

        # Set the end time of the cycle
        date = datetime.now()
        end_time = date.hour * 3600 + date.minute * 60 + date.second

        # Send transaction to smart meter, asking for grid and panel timeseries in the specified interval
        print("Device is turned off, send transaction to smart meter")
        try:
            print("Sending SM_REQUEST transaction to smart meter " + "SM01" + "...")
            print(start)
            subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " +
                                     DEVICE_ID + " " + chosen["panel_id"] + " " + str(cycle) + " " + str(start) + " " + "SM_REQUEST" + " " +
                                     str(chosen["start_time"]) + " " + str(end_time) + " " + device_type + " " + house], shell=True)
            print("SM_REQUEST transaction sent")
            start = start + 1
        except:
            print("Error sending SM_REQUEST transaction")

        # Retrieve data from smart meter
        smData = getData("SM01")
        while (smData is None) or (smData["device_id"] is not DEVICE_ID):
            smData = getData("SM01")

        # update panel reputation - average between new reputation and current reputation
        panelsReputations[smData["panel_id"]] = (calculatePanelReputation(smData["power"]["grid"], smData["power"]["panel"]) + panelsReputations[smData["panel_id"]]) / 2
        FINISH = 1

    # Device is not started yet
    elif(previous_state == readState() == 0):

        try:
            received_data = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel_receiver.js " +
                                                     panelsRoots[chosen["panel_id"]]], shell=True)
            output = json.loads(received_data)
            print(output["data"])
            panelsRoots[chosen["panel_id"]] = output["next_root"]

            if output["data"]["device_id"] == DEVICE_ID:

                # Panel has sent REVOKE and device is off
                if output["data"]["type"] == "REVOKE" and state == 0:
                    # Send REVOKE ACCEPT
                    try:
                        print("Sending REVOKE_ACCEPT transaction to panel " + output["data"]["panel_id"] + "...")
                        subprocess.check_output([
                                                    "node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " +
                                                    DEVICE_ID + " " + chosen["panel_id"] + " " + str(cycle) + " " + str(start) + " " + "REVOKE_ACCEPT" + " " +
                                                    str(0) + " " + str(0) + " " + device_type + " " + house], shell=True)
                        print("REVOKE_ACCEPT transaction sent")
                        start = start + 1
                    except:
                        print("Error sending REQUEST transaction")

                    print("Panel with ID " + chosen["panel_id"] + " has sent REVOKE. Ask to other panels...")
                    #panels.remove(output["data"]["panel_id"])
                    findBestPanel(start, panels)

                # Panel has sent REVOKE and device is on
                elif output["data"]["type"] == "REVOKE" and state == 1:
                    print("I'm working now!")

                    # Send REVOKE DENY
                    try:
                        print("Sending REVOKE_DENY transaction to panel " + output["data"]["panel_id"] + "...")
                        subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/device.js " + DEVICE_ID + " " +
                                                 chosen["panel_id"] + " " + str(cycle) + " " + str(start) + " " + "REVOKE_DENY" + " " + str(0) + " " + str(0) + " " + device_type + " " + house], shell=True)
                        print("REVOKE_DENY transaction sent")
                        start = start + 1
                    except:
                        print("Error sending REQUEST transaction")

                # Panel has sent INIT
                elif output["data"]["type"] == "PANEL_INIT":
                    print("Panel " + output["data"]["panel_id"] + " is active")
                    print(output["data"])

            else:
                print("Ignoring transaction")
        except:
            print("No more data")

    time.sleep(5)
