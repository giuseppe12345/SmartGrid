import time
import subprocess
import json
from datetime import datetime

PANEL_ID = 'P01'

# transaction index
start = 1

# Devices list (included smart meter)
devices = ["D01", "D02", "D03", "D04", "D05", "SM02"]

# They need to start listening to devices' channels
devicesRoots = {
    "D01": "XIICENUBIQNKIYX99WJGAAXYCIGGMWESPXGZYACAJENHXGRCEZLFFZPLBCXRPGWIZLTSWYVUEPOKUYUSU",
    "D02": "WGVLZDBCMFGCEYA9QRNKVGLA9AZRPUAZAS9OCENFQQGIESVEDVEJNKUQWMOPOTMKTGMM9DAHKYJIVRLWH",
    "D03": "YKDCRHXABZN9NBIHEJCAJUFMGCFUMLIDHQKDBJYURPMRAIGCBCBYVDRMPSIQGRYGHDIS9MBLI9ZPUJEZN",
    "D04": "ZZLCBWUMNIDUUVCPESXNRWVQ9R9ANW99WJYNDWTWIJVIJ9LHGTOEXRDIWWQLRZTSTU9FFJALGOOJJPZEZ",
    "D05": "KCNKHCHJTXOIVAOZBQACKHPYF9EWOCY9QYUAOBHO9DDHOPJTGFTXMSHXRGHVLBPDQNRCOHAPSKLVSGKXZ",
    "SM02": "MOJUJZPAYCSSFJQFNQ9LNDUGZUXPZYIDWPYJWSHNTVWGJIEKXWCZMSHSTXF9UDONEPRCUNOJZMEXK9KMO"
}

# Devices reputations (device_id: reputation_value)
devicesReputations = {
   "D01": 0.0,
   "D02": 0.0,
   "D03": 0.0,
   "D04": 0.0,
   "D05": 0.0
}

# It contains panel production profile in the next 24h (86400 element, one for each second)
productionProfile = []

# It contains sum of all device timeseries provisioned by the panel in the next 24h (86400 element, one for each second)
consumptionProfile = []

# It contains a list of busy power by devices (device_id, device_timeserie, assigned_score, state (ACCEPTED/DENIED))
busyPower = {
    "ID01":
    {
        "Timeserie": "json_timeserie",
        "Score": "score of timeserie",
        "Starting_time": "time when device is scheduled to start",
        "State": "ACCEPTED", # EVALUATE, PENDING, ACCEPTED, STARTED
        "Device_to_revoke": "Waiting ID device when State = EVALUATE, NONE otherwise",
        "Cycle_ID": "request_id",
        "Earliest_start": "earliest_start",
        "Latest_start": "latest_start",
        "Working_time": "working_time"
    }
}

# This function calculate the score of panel
def panelScore(new_estimated, earliest, latest, working, new_device_id):

    score = 0
    starting_time = 0
    device_to_revoke = 'None'

    # 1. Function shift without remove any device
    #
    for i in range(earliest, latest):

        # calculateDeviceReputation accepts two array containing object like {"Time": time_value, "Power": power_value},
        # so we need to fill array with element in that form
        # This object represents panel free energy
        free_energy_json = []

        # Get free energy from earliest start to earliest start + working time (at first step).
        # The next step get free energy from (earliest start + 1) and (earliest start + 1 + working time), and so on
        # The length does't change, it is always working time seconds.
        k = 0
        for j in range(i, i + working):
            free_power_sample = productionProfile[j] - consumptionProfile[j]
            # Create json object to pass to calculateDeviceReputation
            free_energy_json.append({"Time": j, "Power": free_power_sample})

            if free_power_sample < 0:
                free_energy_json.append({"Time": k, "Power": 0})

            else:
                # Create json object to pass to calculateDeviceReputation
                free_energy_json.append({"Time": k, "Power": free_power_sample})
            k = k + 1

        # Check if current score is the best, in this case update reputation and starting time
        temp_score = calculateDeviceReputation(new_estimated, free_energy_json)
        if temp_score > score:
            score = temp_score
            starting_time = i

    # 2. Function shift removing one device a time, if its reputation is lower than new one end device doesn't started yet (same concet of the previous steps)
    for key in busyPower:
        if (devicesReputations[key] < devicesReputations[new_device_id]) and busyPower[key]["State"] != "STARTED":
            new_consumption_profile = []
            for sample_power in busyPower[key]["Timeserie"]:
                new_consumption_profile.append(consumptionProfile[sample_power["Time"]] - sample_power["Power"])

            # Function shift
            for i in range(earliest, latest):

                # calculateDeviceReputation accepts two array containing object like {"Time": time_value, "Power": power_value}
                # This object represents panel free energy
                free_energy_json = []

                # Get free energy from earliest start to earliest start + working time (at first step)
                k = 0
                for j in range(i, i + working):
                    # The difference between the previous case is that free_power_sample doesn't contain new_consumption_profile timeserie
                    free_power_sample = productionProfile[j] - consumptionProfile[j] + new_consumption_profile[j]
                    # Create json object to pass to calculateDeviceReputation

                    if free_power_sample < 0:
                        free_energy_json.append({"Time": k, "Power": 0})

                    else:
                        # Create json object to pass to calculateDeviceReputation
                        free_energy_json.append({"Time": k, "Power": free_power_sample})

                    k = k + 1

                # Check if current score is the best, in this case update reputation and starting time
                temp_score = calculateDeviceReputation(new_estimated, free_energy_json)
                if temp_score > score:
                    score = temp_score
                    starting_time = i
                    device_to_revoke = key

    return {"score": score, "starting_time": starting_time, "device_to_revoke": device_to_revoke}


def calculateDeviceReputation(estimated_timeserie, real_timeserie):
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


while True:

    for device in devices:
        try:
            received_data = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel_receiver.js " +
                                                     devicesRoots[device]], shell=True)
            output = json.loads(received_data)
            #print(output["data"])
            devicesRoots[device] = output["next_root"]

            if output["data"]["panel_id"] == PANEL_ID:
                if output["data"]["type"] == "REQUEST":
                    print("REQUEST from device " + output["data"]["device_id"])

                    # Calculate score which optimizes panel utilization
                    score_result = panelScore(output["data"]["power"], output["data"]["earliest_start"], output["data"]["latest_start"], output["data"]["working_time"], output["data"]["device_id"])
                    print(score_result)

                    # If better score is obtained without remove devices
                    if score_result["device_to_revoke"] == "None":
                        try:
                            getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                    str(output["data"]["device_id"]) + " " + str(PANEL_ID) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                                    "PROPOSAL" + " " + str(score_result["score"]) + " " + str(score_result["starting_time"])], shell=True)
                            start = start + 1

                            busyPower[output["data"]["device_id"]] = {
                                "Timeserie": output["data"]["power"],
                                "Score": score_result["score"],
                                "Starting_time": score_result["starting_time"],
                                "State": "PENDING",
                                "Device_to_revoke": "None",
                                "Cycle_ID": output["data"]["request_id"],
                                "Earliest_start": output["data"]["earliest_start"],
                                "Latest_start": output["data"]["latest_start"],
                                "Working_time": output["data"]["working_time"]
                            }
                        except:
                            #print(e.output)
                            print("Error sending PROPOSAL transaction")

                    # If a device has to remove, a REVOKE transaction is sent to it
                    else:
                        busyPower[output["data"]["device_id"]]["Timeserie"] =  output["data"]["power"]
                        busyPower[output["data"]["device_id"]]["Score"] = score_result["score"]
                        busyPower[output["data"]["device_id"]]["Starting_time"]: score_result["starting_time"]
                        busyPower[output["data"]["device_id"]]["State"]: "EVALUATE"
                        busyPower[output["data"]["device_id"]]["Device_to_revoke"] = score_result["device_to_revoke"]
                        busyPower[output["data"]["device_id"]]["Cycle_ID"] = output["data"]["request_id"]
                        busyPower[output["data"]["device_id"]]["Earliest_start"] = output["data"]["earliest_start"]
                        busyPower[output["data"]["device_id"]]["Latest_start"] = output["data"]["latest_start"]
                        busyPower[output["data"]["device_id"]]["Working_time"] = output["data"]["working_time"]

                        try:
                            getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                    str(score_result["device_to_revoke"]) + " " + str(PANEL_ID) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                                    "REVOKE" + " " + str(0) + " " + str(0)], shell=True)
                            start = start + 1
                        except:
                            #print(e.output)
                            print("Error sending REVOKE transaction")


                elif output["data"]["type"] == "ACCEPT":
                    print("Device " + output["data"]["device_id"] + " has accepted proposal, change its state to ACCEPTED")
                    # Change state to ACCEPTED
                    busyPower[output["data"]["device_id"]]["State"] = "ACCEPTED"

                elif output["data"]["type"] == "DENY":
                    print("Device " + output["data"]["device_id"] + " has denied proposal, remove from busyPower list")
                    del busyPower[output["data"]["device_id"]]

                elif output["data"]["type"] == "DEVICE_INIT":
                    print("Device " + output["data"]["device_id"] + " is active")
                    print(output["data"])

                elif output["data"]["type"] == "FINISH":
                    print("Device " + output["data"]["device_id"] + " has finished his cycle, free busy energy...")
                    # Remove device timeserie from consumption list and busy power dict

                    for element in busyPower[output["data"]["device_id"]]["Timeserie"]:
                        consumptionProfile[element["Time"]] = consumptionProfile[element["Time"]] - element["Power"]

                    # Remove entry from busy list
                    del busyPower[output["data"]["device_id"]]
                    print("Ask consumed energy profile to smart meter...")

                    # Send transaction to smart meter
                    # Set the end time of the cycle
                    date = datetime.now()
                    end_time = date.hour * 3600 + date.minute * 60 + date.second

                    try:
                        print("Sending SM_REQUEST transaction to smart meter " + "SM02" + "...")
                        print(start)
                        subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                    output["data"]["device_id"] + " " + PANEL_ID + " " + str(output["data"]["request_id"]) + " " + str(start) + " " + "SM_REQUEST" + " " +
                                                    str(busyPower[output["data"]["device_id"]]["Starting_time"]) + " " + str(end_time)], shell=True)
                        print("SM_REQUEST transaction sent")
                        start = start + 1
                    except:
                        print("Error sending SM_REQUEST transaction")

                elif output["data"]["type"] == "PANEL_RESPONSE":
                    print("Smart meter has sent his data")
                    # Update device reputation
                    devicesReputations[output["data"]["device_id"]] = calculateDeviceReputation(busyPower[output["data"]["device_id"]]["Timeserie"], output["data"]["power"])

                elif output["data"]["type"] == "REVOKE_ACCEPT":
                    print("Device has not started its cycle yet")
                    # Remove device ID entry from busyPower list and accept the evaluated one(s) (if present)
                    del busyPower[output["data"]["device_id"]]

                    # Check if Evaluate Requests can be changed to Pending
                    for key in busyPower:
                        if key["State"] == "EVALUATE":
                            # There is a waiting device
                            if key["Device_to_revoke"] != "None":
                                key["Device_to_revoke"] = "None"

                            # No device has to be waited for accepting revoke, PROPOSAL transaction can be sent
                            else:
                                key["State"] = "PENDING"
                                try:
                                    getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                                       str(key) + " " + str(PANEL_ID) + " " + str(key["Cycle_ID"]) + " " +
                                                                       str(start) + " " + "PROPOSAL" + " " + str(key["Score"]) + " " + str(key["Starting_time"])], shell=True)
                                    start = start + 1
                                except:
                                    # print(e.output)
                                    print("Error sending PROPOSAL transaction")

                elif output["data"]["type"] == "REVOKE_DENY":
                    print("Device has already started its cycle")
                    busyPower[output["data"]["device_id"]]["State"] = "STARTED"

                    # Calculate score which optimizes panel utilization, excluding the device who has sent REVOKE_DENY
                    score_result = panelScore(output["data"]["power"], output["data"]["earliest_start"],
                                              output["data"]["latest_start"], output["data"]["working_time"],
                                              output["data"]["device_id"])

                    # If better score is obtained without remove devices
                    if score_result["device_to_revoke"] == "None":
                        try:
                            getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                               str(output["data"]["device_id"]) + " " + str(PANEL_ID) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                                                  "PROPOSAL" + " " + str(score_result["score"]) + " " + str(score_result["starting_time"])], shell=True)
                            start = start + 1

                            busyPower[output["data"]["device_id"]] = {
                                "Timeserie": output["data"]["power"],
                                "Score": score_result["score"],
                                "Starting_time": score_result["starting_time"],
                                "State": "PENDING",
                                "Device_to_revoke": "None",
                                "Cycle_ID": output["data"]["request_id"],
                                "Earliest_start": output["data"]["earliest_start"],
                                "Latest_start": output["data"]["latest_start"],
                                "Working_time": output["data"]["working_time"]
                            }
                        except:
                            # print(e.output)
                            print("Error sending PROPOSAL transaction")

                    # If a device has to remove, a REVOKE transaction is sent to it
                    else:
                        busyPower[output["data"]["device_id"]]["Timeserie"] = output["data"]["power"]
                        busyPower[output["data"]["device_id"]]["Score"] = score_result["score"]
                        busyPower[output["data"]["device_id"]]["Starting_time"]: score_result["starting_time"]
                        busyPower[output["data"]["device_id"]]["State"]: "EVALUATE"
                        busyPower[output["data"]["device_id"]]["Device_to_revoke"] = score_result["device_to_revoke"]
                        busyPower[output["data"]["device_id"]]["Cycle_ID"] = output["data"]["request_id"]
                        busyPower[output["data"]["device_id"]]["Earliest_start"] = output["data"]["earliest_start"]
                        busyPower[output["data"]["device_id"]]["Latest_start"] = output["data"]["latest_start"]
                        busyPower[output["data"]["device_id"]]["Working_time"] = output["data"]["working_time"]

                        try:
                            getData = subprocess.check_output(["node /home/giuseppe/Giuseppe/Codice/Tesi\ Smart\ Grid/smart\_energy\_3/smart\_energy/panel.js " +
                                                               str(score_result["device_to_revoke"]) + " " + str(PANEL_ID) + " " + str(output["data"]["request_id"]) + " " + str(start) + " " +
                                                               "REVOKE" + " " + str(0) + " " + str(0)], shell=True)
                            start = start + 1
                        except:
                            # print(e.output)
                            print("Error sending REVOKE transaction")
            else:
                print("Ignoring transaction")

        except:
            print("No more data")
        time.sleep(5)
