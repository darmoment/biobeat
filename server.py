import firebase_admin
from firebase_admin import credentials, db
import threading

# Load credentials and initialize app
cred = credentials.Certificate("biobeat-2d01c-firebase-adminsdk-fbsvc-23282874f8.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://biobeat-2d01c-default-rtdb.firebaseio.com/'
})

# Function to handle heart rate updates
def heart_rate_listener(event):
    # print("❤️ Heart Rate Update:", event.data)
    average_heart_rates()

# Function to handle vote updates
def vote_listener(event):
    # print("👍 Vote Update:", event.data)
    average_votes()

# Start listening to both, may need to take watches off
def start_listeners():
    db.reference("HeartRates").listen(heart_rate_listener)
    db.reference("Votes").listen(vote_listener)

# Run in separate thread
thread = threading.Thread(target=start_listeners)
thread.start()

def average_heart_rates():
    heart_data = db.reference("HeartRates").get()
    values = []

    for watch_id, entry in heart_data.items():
        values.append(entry['value']['doubleValue'])
    
    avg = sum(values) / len(values) if values else 0
    watch_averages = avg

    print("Heart Averages:", watch_averages)

def average_votes():
    voting_data = db.reference("Votes").get()
    values = []

    for watch_id, entry in voting_data.items():
        values.append(entry['value'])
    
    avg = sum(values) / len(values) if values else 0
    voting_averages = avg

    print("Voting Averages:", voting_averages)
