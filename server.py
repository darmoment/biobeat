# server.py

import firebase_admin
from firebase_admin import credentials, db
import threading, time, os
from openai import OpenAI
import openai_secrets

client = OpenAI(api_key=openai_secrets.SECRET_KEY)

# Globals
prevSong = "Yeah - Usher"
currentSong = "Yeah - Usher"

voting_averages = 0  # Boss's variable name

baseline_hr   = {}
prev_peak_hr  = {}
latest_peaks  = {}
lock = threading.Lock()

# Firebase setup
cred = credentials.Certificate("biobeat-2d01c-firebase-adminsdk-fbsvc-23282874f8.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://biobeat-2d01c-default-rtdb.firebaseio.com/'
})


def evaluate_indicators():
    """
    
        It operates on two signals:
    1. Heart rate (HR): If the current peak HR for any watch exceeds both:
        - the watch's baseline (resting) HR, and
        - the previous peak HR,
       then it counts as a **positive** HR indicator.

    2. Votes: If the average vote (from crowd feedback) is positive (>0),
       it counts as a **positive** vote indicator.

       If **either** the HR or the votes show a positive indicator, trigger the positive response
    """
    global prev_peak_hr, latest_peaks, voting_averages

    hr_positive = False
    with lock:
        if latest_peaks:
            crowd_peak = max(latest_peaks.values())
            crowd_id   = max(latest_peaks, key=latest_peaks.get)

            if crowd_id not in baseline_hr:
                baseline_hr[crowd_id]  = crowd_peak
                prev_peak_hr[crowd_id] = crowd_peak

            rest     = baseline_hr[crowd_id]
            previous = prev_peak_hr.get(crowd_id, rest)

            if (crowd_peak > rest) and (crowd_peak > previous):
                hr_positive = True

            prev_peak_hr[crowd_id] = crowd_peak

    vote_positive = voting_averages > 0

    if hr_positive or vote_positive:
        positive_indicators()
    else:
        negative_indicators()


# Firebase listeners
def heart_rate_listener(event):
    average_heart_rates()

def vote_listener(event):
    average_votes()

def start_listeners():
    db.reference("HeartRates").listen(heart_rate_listener)
    db.reference("Votes").listen(vote_listener)

threading.Thread(target=start_listeners, daemon=True).start()


# Aggregation helpers
def average_heart_rates():
    heart_data = db.reference("HeartRates").get()
    if not heart_data:
        return
    with lock:
        for watch_id, entry in heart_data.items():
            hr = entry['value']['doubleValue']
            latest_peaks[watch_id] = max(hr, latest_peaks.get(watch_id, 0))
        avg = sum(latest_peaks.values()) / len(latest_peaks)
    print("Heart-rate average:", round(avg, 1))
    evaluate_indicators()

def average_votes():
    global voting_averages
    voting_data = db.reference("Votes").get()
    values = []

    for watch_id, entry in voting_data.items():
        values.append(entry['value'])
    
    avg = sum(values) / len(values) if values else 0
    voting_averages = avg

    print("Vote average:", round(voting_averages, 2))
    evaluate_indicators()


# Music alteration functions
def positive_indicators():
    global currentSong, prevSong

    prompt = (
        f"You are a DJ at a party. Your audience is showing a positive response to the song {currentSong}. "
        f"Give me a similar song to play that is different from {prevSong} and {currentSong}. "
        f"Format it as: Name of Song - Name of Artist"
    )
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
    )
    response = resp.choices[0].message.content.strip()
    prevSong = currentSong
    currentSong = response
    print("▶️  Switching to (positive):", response)
    return response

def negative_indicators():
    global currentSong, prevSong

    prompt = (
        f"You are a DJ at a party. Your audience is showing a negative response to the song {currentSong}. "
        f"Give me a different song to play that is different from {prevSong} and {currentSong}. "
        f"Format it as: Name of Song - Name of Artist"
    )
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
    )
    response = resp.choices[0].message.content.strip()
    prevSong = currentSong
    currentSong = response
    print("▶️  Switching to (negative):", response)
    return response


# Main program loop
if __name__ == "__main__":
    start_listeners()
    which_program = input("Which program would you like to run? \n Heart Rate (h), Voting system (v), or monitoring (m)? \n")
    
    try:
        while True:
            if which_program == "h":
                # Heart Rate Algo (driven by listener)
                print("Listening for heart rate changes...")
                time.sleep(10)

            elif which_program == "v":
                # Voting Algo
                user_input = input("Is it time to change the song? (y)\n")
                if user_input == "y":
                    if voting_averages > 0.5:
                        positive_indicators()
                    else:
                        negative_indicators()

            elif which_program == "m":
                # Manual Monitoring
                user_input = input("Change the song positively (p) or negatively (n)? \n")
                if user_input == "p":
                    positive_indicators()
                elif user_input == "n":
                    negative_indicators()

    except KeyboardInterrupt:
        print("Shutting down…")
