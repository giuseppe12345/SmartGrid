# File read_timeserie.py

1. Si creano due tabelle in un database MySQL con le seguenti colonne:
	columnsTimeseries = ["Cycle_ID", "Earliest_Start", "Latest_Start", "Working_Time"]
	columnsPower = ["Cycle_ID", "Power", "Time"]

2. Si legge il file completo delle timeserie 'feed_92.MYD.csv' e si aggiunge alla lista 'instant_read' la riga letta nel file, nel formato {"time": time, "power": row[1]}

3. Si legge il file dei cicli 'feed_92.MYD.runs.csv' e per tutte le sue righe si ripetono le seguenti operazioni
	3.1 Per ogni riga all'interno di questo file, si calcolano earliest start, latest_start, working time
		I valori di earliest e latest start sono calcolati come il tempo effetivo letto nel file - 30 minuti e + 30 minuti
	3.2 Si aggiunge nella tabella 'Power' e nella lista power_values la riga fatta con i tre valori calcolati
	3.3 Si aggiunge nella lista cycle un'entry con i tre valori precedenti e la lista power_values
	3.4 Si aggiunge un riga nella tabella Timeseries con gli stessi valori di earliest start, latest_start, working time.
	
