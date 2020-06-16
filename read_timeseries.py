import csv
from datetime import  datetime
import MySQLdb

# Database parameters (to connect from remote host, comment the line 'bind-address = 127.0.0.1')
address = "services.pep.it"
user = "giuseppe"
password = "google7.11"
database = "smart_grid"
tableTimeseries = "Timeseries"
tablePower = "Power"
columnsTimeseries = ["Device_Type", "House", "Cycle_ID", "Earliest_Start", "Latest_Start", "Working_Time"]
columnsPower = ["Device_Type", "House", "Cycle_ID", "Power", "Time"]
db = MySQLdb.connect(address, user, password, database)

#device type and house name
device_type = "washingmachine"
house = "kn07"
file_number = "66"

# Read timeseries file
instant_read = []
with open('../palermo/' + device_type + '/' + house + '/feed_' + file_number + '.MYD.csv') as timeseries_file:
    timeseries_reader = csv.reader(timeseries_file, delimiter=' ')
    line_count = 0
    for row in timeseries_reader:
        print("Timestamp: " + row[0] + '\t' + "Power: " + row[1])
        date = datetime.fromtimestamp(int(row[0]))
        time = date.hour*3600 + date.minute*60 + date.second
        instant_read.append({"time": time, "power": row[1]})
        print(instant_read[line_count])
        line_count = line_count + 1

    #print(f'Processed {line_count} lines.')


# Read cycles interval
cycles = []

with open('../palermo/' + device_type + '/' + house + '/feed_' + file_number + '.MYD.csv.runs') as intervals_file:
    intervals_reader = csv.reader(intervals_file, delimiter=',')
    line_count = 0
    for row in intervals_reader:
        #print('Start row: ' + row[0] + '\t\t' + "End row: " + row[1])
        earliest_start = int(instant_read[int(row[0])]["time"] - 1800)
        latest_start = int(instant_read[int(row[0])]["time"] + 1800)
        working_time = int(instant_read[int(row[1])]["time"] - instant_read[int(row[0])]["time"])
        power_values =[]

        cursor = db.cursor()
        for i in range(int(row[0]), int(row[1])):
            power_values.append(instant_read[i]["power"])
            cursor.execute("INSERT INTO " + tablePower + " (" + columnsPower[0] + ", " + columnsPower[1] + ", " + columnsPower[2] + "," + columnsPower[3] + "," + columnsPower[4] + ") VALUES(%s, %s, %s, %s, %s)",
                           [device_type, house, line_count, instant_read[i]["power"], instant_read[i]["time"]])
            db.commit()

        cycles.append({"earliest_start": earliest_start,
                       "latest_start": latest_start,
                       "working_time": working_time,
                       "power": power_values
                       })
        print(cycles[line_count])

        cursor.execute("INSERT INTO " + tableTimeseries + " (" + columnsTimeseries[0] + "," + columnsTimeseries[1] + "," + columnsTimeseries[2] + "," + columnsTimeseries[3] + "," + columnsTimeseries[4] + "," + columnsTimeseries[5] + ") VALUES(%s, %s, %s, %s, %s, %s)",
                       [device_type, house, line_count, earliest_start, latest_start, working_time])
        db.commit()

        line_count = line_count + 1

    #print(f'Processed {line_count} lines.')



