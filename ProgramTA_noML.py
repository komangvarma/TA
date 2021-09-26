#importing modules
import mysql.connector
from datetime import datetime
import csv
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import messagebox, filedialog
import os 
from PIL import ImageTk, Image

#connect to MySQL database 
db = mysql.connector.connect(
	host="localhost",
	user="root",
	password="cagalli3",
	database="productiontime"
	)

mycursor = db.cursor() #define the database cursor

#define the setup record switch button is on
global is_on
is_on = True;

total_bda = 0.0;
total_pst = 0.0;
total_ust = 0.0;
total_rsa = 0.0;
total_ssa = 0.0;
total_at = 0.0;

#define SetupSwitch function for setup recording button
def SetupSwitch(): 
	global is_on 
	#condition if it is on or off
	if is_on: #the button clicked at "on" condition
		#update setup status and start time into productionlog table
		mycursor.execute("""UPDATE productionlog SET setup_status = %s, start_time = %s 
							WHERE status = 'Taken' LIMIT 1""", ('Recording', datetime.now()))
		#remove the recent taken workpiece
		mycursor.execute("DELETE FROM productionlog order by product_no desc limit 1")
		db.commit() #confirm the executed data value
		on_button.config(image=off_new) #change the button image into "stop recording"
		record_label.config(text="Recording...", fg="red") #change the label above the button into "Recording"
		is_on = False; #the button become "off" condition

	else: #the button clicked at "off" condition
		#update setup status and finish time into productionlog table
		mycursor.execute("""UPDATE productionlog SET setup_status = %s, finish_time = %s 
							WHERE setup_status = 'Recording' LIMIT 1""", ('Recorded', datetime.now()))

		#insert the new 'Taken Time' for recent workpiece
		mycursor.execute("""INSERT INTO productionlog (status, taken_time, start_time, finish_time) 
							VALUES (%s,%s,%s,%s)""", ('Taken', datetime.now(), 0, 0))
		db.commit()
		on_button.config(image=on_new) #change the button image into "start recording"
		#change the label above the button into "Setup Time Recorded!"
		record_label.config(text="Setup Time Recorded!", fg="black") 
		is_on = True; #the button back into "on" condition

#define enter_description function for entering setup description
def enter_description():
	#define SQL query for updating the setup description value into production log table
	enter_sql = """UPDATE productionlog SET setup_status = %s, description = %s 
					WHERE setup_status = 'Recorded' LIMIT 1"""

	setup_status = 'Done' #define the update value of setup status
	descript = e.get(); #call the entry value of setup description input by user
	put = (setup_status, descript) #define all value variables into one variable
	mycursor.execute(enter_sql, put) #execute the update SQL query with the value
	db.commit()

#define productionlog function for saving the production log data from MySQL database 
def productionlog():
	#define SQL query for data value calculation on productionlog table
	query = """SELECT product_no, 
				(TIME_TO_SEC(TIMEDIFF(finished_time, taken_time)) 
				- TIME_TO_SEC(TIMEDIFF(finish_time,start_time))) * 2.47 AS 'Elapsed Time(s)',
				TIME_TO_SEC(TIMEDIFF(finish_time, start_time)) AS 'Setup Time(s)',
				description
			FROM productionlog"""
	mycursor.execute(query) #execute the calculation query
	
	res = mycursor.fetchmany(12) #fetch the result of calculation within maximum 12 rows
	mydata = len(res) #define the length of fetched result

	#condition if the result data length is available or not
	if mydata < 1: #make sure there is data available
		messagebox.showerror("No Data", "No data available to be saved") #showing error message box

	else: #data is available
	#store fetched calculated values from database into csv file
		#define the file name from file dialogue that is saved by user
		fn = filedialog.asksaveasfilename(initialdir = os.getcwd(), title='Save Data', \
			filetypes=(("CSV File", "*.csv"),("All Files", "*.*"))) 
		with open(fn,'w', newline="") as fileout: #open the new csv file
			writer = csv.writer(fileout) #define the csv writer
			writer.writerows(res) #write every row in loop

		messagebox.showinfo("Data Saved!", "Your data have been saved successfully.") #showing succesfull message box

#define production_report function for calculating the time loss and will be classified into each Six Big Losses category 
def production_report():	
	#open the csv file name from file dialogue that is saved
	fn = filedialog.askopenfilename(initialdir = os.getcwd(), title='Open File',\
	 filetypes=(("CSV File", "*.csv"),("All Files", "*.*")))
	with open(fn, 'r') as f:
		reader = csv.reader(f, delimiter=',', quotechar='"') #define the csv reader
		next(reader) #read every row on csv file
		#define useful variables for time loss calculation
		global total_pst
		global total_ssa
		global total_ust
		global total_bda
		global total_rsa
		global total_at
		total_bda = 0.0;
		total_pst = 0.0;
		total_ust = 0.0;
		total_rsa = 0.0;
		total_ssa = 0.0;
		total_at = 0.0;
		bda = 0.0;
		ssa = 0.0;
		rsa = 0.0;
		for row in reader: 
			if row: #condition if the row is available
				at = float(row[1]) #define the elapsed arm time column
				st = float(row[2]) #define the setup time column
				total_at += at; #accumulate every elapsed arm time value
				iat = 51.9; #define the ideal cycle arm time
				#define the percentage of actual elapsed arm time formula in every row:
				actual_arm_time = float((at / iat) * 100); 
				loss_arm = float(at - iat); #define the time loss formula in every row
				if actual_arm_time >= 200: #if the actual time percentage is >= 200% of ideal cycle time
					total_bda += loss_arm; #accumulate the time loss into breakdowns category
					total_ust += st; #accumulate the setup time loss into unplanned setup and adjustment category
				
				elif actual_arm_time >= 150:#if the actual time percentage is >= 150% of ideal cycle time
					total_ssa += loss_arm; #accumulate the time loss into small stops category
					total_ust += st;
				
				elif actual_arm_time >= 120:#if the actual time percentage is >= 120% of ideal cycle time
					total_rsa += loss_arm; #accumulate the time loss into reduced speed category
					total_ust += st;
				
				else: #if the actual time percentage is below 120% of ideal cycle time
					total_pst += st; #accumulate the setup time loss into planned stop time

	#define the total unplanned stop time loss formula within 2 maxiumum decimal number
	arm = round((total_bda + total_ssa + total_rsa + total_ust),2); 
	#define the total planned stop time loss percentage formula within 2 maxiumum decimal number
	p_setup = round((float(total_pst / total_at) * 100), 2); 

	if arm == 0: #condition if total unplanned stop time loss is 0
		#define the string variable for tkinter window output label:
		time_loss_arm = 'total planned time loss: ' + str(total_pst) + ' s (' + str(p_setup) + '%)' + \
		"\n there is no Unplanned time loss on Industrial Robot Arm"
		loss_spec_arm = '' 

	else: #if total unplanned stop time loss exist

		#define the unplanned stop time loss percentage value formulation for each Six Big Losses category:
		bda = round(((total_bda/arm) * 100),2); #breakdowns percentage
		ssa = round(((total_ssa/arm) * 100),2); #small stops percentage
		rsa = round(((total_rsa/arm) * 100),2); #reduced speed percentage
		u_setup = round((float(total_ust / arm)* 100), 2); #unplanned setup and adjustment percentage
		
		#define the string variable for tkinter window output label:
		time_loss_arm = 'total planned time loss: ' + str(total_pst) + ' s (' + str(p_setup) + '%)' + \
		"\ntotal unplanned time loss on Industrial Robot Arm: " + str(arm) + ' s'
		loss_spec_arm = '\nbreakdowns = ' + str(total_bda) + ' s (' + str(bda) + '%)' + \
		'\nsetup and adjustment = ' + str(total_ust) + ' s (' + str(u_setup) + '%)'+ \
		'\nsmall stops = ' + str(total_ssa) + ' s (' + str(ssa) + '%)' + \
		'\nreduced speed = ' + str(total_rsa) + ' s (' + str(rsa) + '%)' 
	
	#tkinter window output label 
	label['text'] = time_loss_arm + loss_spec_arm 
	
	#define the treeview funtion for displaying output table of production log
	def treeview_sort_column(tv, col, reverse): #define the sorting column function
		l = [(tv.set(k, col), k) for k in tv.get_children('')]
		l.sort(reverse=reverse)

		# rearrange rows in sorted positions
		for index, (val, k) in enumerate(l):
			tv.move(k, '', index)

    	# reverse sort next time
		tv.heading(col, command=lambda _col=col: treeview_sort_column(tv, _col, not reverse))

	columns = (1,2,3,4) #define number of columns on treeview
	#define the treeview table variable
	tv = ttk.Treeview(side_frame, columns=columns,show='headings', height=26)	
	for col in columns: #loop on every column
		#setting the treeview heading for each column
		tv.heading(col, text=col,command=lambda _col=col: treeview_sort_column(tv, _col, False))
	tv.pack() #make the treeview displayed in the Tkinter window
	#Setting every column heading style:
	tv.heading(1, text="Product No.")
	tv.column(1, width = 100, stretch = NO)
	tv.heading(2, text="Elapsed Time(s)")
	tv.column(2, width = 100, stretch = NO)
	tv.heading(3, text ="Setup Time (s)")
	tv.column(3, width = 100, stretch = NO)
	tv.heading(4, text = "Setup Description(s)")
	tv.column(4, width = 300, stretch = NO)

	with open(fn, 'r') as f: #open the saved csv file
		reader = csv.reader(f, delimiter=',') 
		for row in reader:
			#define each column value in every row of csv file:
			product_no = row[0] #frist column
			elapsed_time = row[1] #second column
			setup_time = row[2] #third column
			description = row[3] #fourth column
			#inserting values from csv file into treeview
			tv.insert("", 0, values=(product_no, elapsed_time, setup_time, description))

def saveproduction():
	
	insquery = """INSERT INTO productionreport (breakdowns, slow_cycles, small_stops, planned_downtime, operation_time) 
	VALUES (%s,%s,%s,%s,%s)"""
	putins = (total_bda, total_rsa, total_ssa, total_pst, total_at)
	mycursor.execute(insquery, putins)
	db.commit()

	print(total_ust, total_pst, total_rsa, total_bda, total_ssa)
#define the Tkinter window for user interface
window = Tk() #window as the Tkinter root
#define the default size of Tkinter window
canvas = Canvas(window, height=600, width=600)
canvas.pack() 
#define the setup time record label above the switch button
record_label = Label(window, text="Record Setup Time")
record_label.place(x=260,y=20)
#define the switch button images:
#set image when the switch button is on:
on = Image.open("images/Record.png")
on_resized = on.resize((70,70), Image.ANTIALIAS)
on_new = ImageTk.PhotoImage(on_resized)
#set image when the switch button is off:
off = Image.open("images/StopButton.png")
off_resized = off.resize((90,90), Image.ANTIALIAS)
off_new = ImageTk.PhotoImage(off_resized)
#define switch button for setup time recording
on_button = Button(window, image=on_new, bd=2, width= 70, height= 70, command=SetupSwitch)
on_button.place(x= 275, y=50)
#define the entry input frame
e = Entry(window, width = 50)
e.place(x=20, y=150, relwidth=0.9)
e.insert(0, "Enter Setup Description") #inserting initial label on the  input frame
#define the enter  setup description button
enter_button= Button(window, text="Enter Setup Description", command=enter_description)
enter_button.place(x=430, y=170)
#define the save production log button
recordbutton = Button(window, text="Save Production Log", command=productionlog)
recordbutton.place(x=20, y=200)
#define the show production report button
sp_button = Button(window, text="Show Production Report", command=production_report)
sp_button.place(x=150,y=200)
#define the display frame for displaying production report result
side_frame = Frame(window, bg='white', bd=10, width = 400, height=300)
side_frame.place(x=20, y=230, relwidth=0.9, relheight= 0.6)
#define the label that would be written on the display frame
label = Label(side_frame, bg='white')
label.pack()

save_production_button= Button(window, text="Save Production Report", command=saveproduction)
save_production_button.place(x=300, y=200)

window.mainloop() #run the tkinter window in loop