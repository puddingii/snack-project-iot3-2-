import RPi.GPIO as GPIO
import numpy as np
from bottle import route, run, template, static_file
import matplotlib.pyplot as plt
import MySQLdb
import datetime
import time
import cv2

#GPIO & pins setting
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
trig = 24
echo = 25
GPIO.setup(trig,GPIO.OUT)
GPIO.setup(echo,GPIO.IN)
control_pins = [12,16,20,21]
for pin in control_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)
now_time = datetime.datetime.now().strftime('%Y-%m-%d')
db = MySQLdb.connect("localhost","pi","raspberry","project")
cur = db.cursor()
cur.execute("select count(*) from eat;")
DB_count = cur.fetchone()[0] + 1
cur.close()
db.close()

#Add DB
def db_addData(channel):
    print("Waiting.... adding data at DB...")
    global DB_count
    leng = "insert into eat values("
    leng = leng + str(DB_count) + ",\'"+now_time+"\');"
    db = MySQLdb.connect("localhost","pi","raspberry","project")
    cur = db.cursor()
    cur.execute(leng)
    DB_count += 1
    db.commit()
    cur.close()
    db.close()
    print("Finished add")
    

#step moter setting
halfstep_seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]
def moter_detect(channel):
    global halfstep_seq, control_pins
    print("moter is activation")
    for i in range(256):
        for halfstep in range(8):
            for pin in range(4):
                GPIO.output(control_pins[pin], halfstep_seq[halfstep][pin])
            time.sleep(0.001)

#face detect setting

def btn_detect(channel):
    print("btn_detect")
    #face detect library
    faceCascade= cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0) #find web cam
    face_count = 0
    global data_count
    while True:
        ret, img = cap.read()  #image file read
        #img = cv2.flip(img, -1) #top, bottom reverse
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) #invert gray image
        faces = faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,   #max 5 people detect
            minSize=(20, 20)  #min of face size
        )
        for (x, y, w, h) in faces:  #if face is existing, get face values
            cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
            #image, center of circle, radius,color, line size
            cv2.imwrite("person_data/data_"+str(face_count)+"_"+now_time+".jpg",gray[y:y+h,x:x+w])
            face_count += 1
            print(str(face_count)+"is stored")
        if face_count == 5:
            face_count = 0
            break 
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    print("exit btn_detect")
    moter_detect(1)
    db_addData(1)

GPIO.add_event_detect(23, GPIO.RISING, callback=btn_detect, bouncetime=1000)

homepage = '''
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ho+j7jyWK8fNQe+A12Hb8AhRq26LrZ/JpcUGGOn+Y7RsweNrtN/tE3MoK7ZeZDyx" crossorigin="anonymous"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous">

<div class="card" style="width: 18rem;">
    <img src="{{image}}" class="card-img-top" alt="image">
    <div class="card-body">
        <h5 class="card-title">Snack</h5>
        <p class= "card-text">
        % if today_sn > 7:
            Too many eat snacks!!!
        % else:
            Eat few snacks...Good!!
        % end
        </p>
    </div>
    <ul class="list-group list-group-flush">
        <li class="list-group-item">Today snacks : {{today_sn}}</li>
        <li class="list-group-item">Total snacks : {{total_sn}}    <a href="http://localhost:8080/" class="card-link">Refresh</a></li>
    </ul>
    <div class="card-body">
        <a href="http://localhost:8080/graph" class="card-link">Graph</a>
        <a href="http://localhost:8080/check" class="card-link">Check</a>
        <a href="http://localhost:8080/camera" class="card-link">Compare</a>
    </div>
</div>
'''

@route('/')
def index():
    global now_time, DB_count
    now_time = datetime.datetime.now().strftime('%Y-%m-%d')
    db = MySQLdb.connect("localhost","pi","raspberry","project")
    cur = db.cursor()
    cur.execute("select count(*) from eat where time='"+now_time+"';")
    tod_sn = cur.fetchone()[0]
    cur.execute("select count(*) from eat;")
    DB_count = cur.fetchone()[0] + 1
    cur.close()
    db.close()
    img = ""
    if tod_sn > 7:
        img = "./static/pig.jpeg"
    else:
        img = "./static/snack.jpeg"
    return template(homepage,today_sn=tod_sn,total_sn=DB_count-1, image=img)

@route('/graph')  #eating snacks count graph
def snack_grp():
    dataX_label = []
    valueY_label = []
    db = MySQLdb.connect("localhost","pi","raspberry","project")
    cur = db.cursor()
    cur.execute("select * from eat;")
    
    data_chk = cur.fetchone()
    cnt_data=0
    if data_chk:
        cnt_data = 1
        dataX_label.append(str(data_chk[1]))
        data_chk = data_chk[1]
    else:
        print("no values in table")
        return
    
    while True:
        value = cur.fetchone()
        if not value:
            valueY_label.append(cnt_data)
            break
        if data_chk != value[1]:
            data_chk = value[1]
            dataX_label.append(str(value[1]))
            valueY_label.append(cnt_data)
            cnt_data = 0
        cnt_data += 1
    cur.close()
    db.close()
    plt.plot(dataX_label, valueY_label)
    plt.scatter(dataX_label, valueY_label)
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.title("Snacks Count")
    plt.show()
    return '<a href="http://localhost:8080/" class="card-link">Return Home</a>'

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='/home/pi/project/person_data')

camera_html = '''
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ho+j7jyWK8fNQe+A12Hb8AhRq26LrZ/JpcUGGOn+Y7RsweNrtN/tE3MoK7ZeZDyx" crossorigin="anonymous"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous">

<a href="http://localhost:8080/" class="card-link">Return Home</a>

<div class="card-group">
    <div class="card">
        <img src="./static/data_0_{{previous}}.jpg" class="card-img-top">
        <div class="card-body">
            <h5 class="card-title">Previous capture</h5>
        </div>
    </div>
    <div class="card">
        <img src="./static/data_0_{{current}}.jpg" class="card-img-top">
        <div class="card-body">
            <h5 class="card-title">Current capture</h5>
        </div>
    </div>
</div>
'''

@route('/camera')
def camera():
    dataX_label = []
    db = MySQLdb.connect("localhost","pi","raspberry","project")
    cur = db.cursor()
    cur.execute("select * from eat;")
    
    data_chk = cur.fetchone()
    if data_chk:
        dataX_label.append(data_chk[1])
        data_chk = data_chk[1]
    else:
        print("no values in table")
        return
    
    while True:
        value = cur.fetchone()
        if not value:
            break
        if data_chk != value[1]:
            data_chk = value[1]
            dataX_label.append(value[1])
    cur.close()
    db.close()
    first_camera = dataX_label[0]
    last_camera = dataX_label[len(dataX_label)-1]
    
    return template(camera_html,previous=first_camera,current=last_camera)

check_snack = '''
    <p>
    % if dis > 5:
        Please refill snacks
    % else:
        Need not refill
    % end
    </p>
    <br>
    <a href="http://localhost:8080/" class="card-link">Return Home</a>
'''

@route('/check')  #snack amount check
def check_bottle():
    data = 0
    for i in range(10):
        GPIO.output(trig, False)
        time.sleep(0.5)
        GPIO.output(trig, True)
        time.sleep(0.00001)
        GPIO.output(trig,False)

        while GPIO.input(echo) == False:
            pulse_start = time.time()

        while GPIO.input(echo) == True:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17000
        distance = round(distance, 2)
        print("Distance : ",distance, "cm")
        data = data + distance
    data = data / 10
    return template(check_snack, dis=distance)

run(host='localhost', port=8080)
print("localhost exit")
GPIO.cleanup()
print("GPIO exit")
