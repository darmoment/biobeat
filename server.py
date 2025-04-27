import firebase_admin
from firebase_admin import credentials, db
import threading

#for gpt
import os
from openai import OpenAI
import openai_secrets
client = OpenAI(api_key=openai_secrets.SECRET_KEY)
import time

# Starting Song
currentSong = "Yeah - Usher"

# ---* Reading data for Heart Rates and Voting *---

cred = credentials.Certificate("biobeat-2d01c-firebase-adminsdk-fbsvc-23282874f8.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://biobeat-2d01c-default-rtdb.firebaseio.com/'
})

def heart_rate_listener(event):
    average_heart_rates()

def vote_listener(event):
    average_votes()

# Start listening to both, may need to take watches off
def start_listeners():
    db.reference("HeartRates").listen(heart_rate_listener)
    db.reference("Votes").listen(vote_listener)

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



# ---* Music Alteration Functions *---

def positive_indicators():
    global currentSong

    prompt = (
        f"You are a DJ at a party.  Your audience is showing a positive response to the song {currentSong}."
        f"Give me a similar song to play. Format it in the following way: Name of Song - Name of Artist"
    )

    response_raw = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )

    response = response_raw.choices[0].message.content
    print(response)
    currentSong = response
    return response

def negative_indicators():
    global currentSong

    prompt = (
        f"You are a DJ at a party.  Your audience is showing a negative response to the song {currentSong}."
        f"Give me a different song to play. Format it in the following way: Name of Song - Name of Artist"
    )

    response_raw = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )

    response = response_raw.choices[0].message.content
    print(response)
    currentSong = response
    return response

# ---* Main Program *---

if __name__ == "__main__":

    start_listeners()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")