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
watch_averages = 0
storing_avg_heartrate = []

lock = threading.Lock()

# Firebase setup
cred = credentials.Certificate("biobeat-2d01c-firebase-adminsdk-fbsvc-23282874f8.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://biobeat-2d01c-default-rtdb.firebaseio.com/'
})


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
    global watch_averages

    heart_data = db.reference("HeartRates").get()
    values = []

    for watch_id, entry in heart_data.items():
        values.append(entry['value']['doubleValue'])
    
    avg = sum(values) / len(values) if values else 0
    watch_averages = avg

    print("Heart Averages:", watch_averages)

sampling_active = True

def background_sampler():
    global storing_avg_heartrate
    while True:
        if sampling_active:
            heart_data = db.reference("HeartRates").get()
            values = []

            for watch_id, entry in heart_data.items():
                values.append(entry['value']['doubleValue'])

            if values:
                avg = sum(values) / len(values)
                storing_avg_heartrate.append(avg)
                print(f"[Sampler] Collected avg: {round(avg, 2)}")

        time.sleep(2)  # Sample every 2 seconds

def average_votes():
    global voting_averages
    voting_data = db.reference("Votes").get()
    values = []

    for watch_id, entry in voting_data.items():
        values.append(entry['value'])
    
    avg = sum(values) / len(values) if values else 0
    voting_averages = avg

    print("Vote average:", round(voting_averages, 2))

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
    threading.Thread(target=background_sampler, daemon=True).start()
    which_program = input("Which program would you like to run? \n Heart Rate (h), Voting system (v), or monitoring (m)? \n")
    
    try:
        while True:
            if which_program == "h":
                print("🔄 Collecting baseline heart rate average for 60 seconds...")

                baseline_values = []
                baseline_duration = 60  # seconds
                sample_interval = 5  # seconds
                num_samples = baseline_duration // sample_interval

                for i in range(num_samples):
                    heart_data = db.reference("HeartRates").get()
                    values = []

                    for watch_id, entry in heart_data.items():
                        values.append(entry['value']['doubleValue'])

                    if values:
                        avg_sample = sum(values) / len(values)
                        baseline_values.append(avg_sample)
                        print(f"Sample {i+1}/{num_samples}: {round(avg_sample, 2)}")

                    time.sleep(sample_interval)

                previous_avg = sum(baseline_values) / len(baseline_values) if baseline_values else 0
                print(f"✅ Baseline average heart rate: {round(previous_avg, 2)}")

                while True:
                    user_input = input("Evaluate heart rate change and suggest song? (y/n): ")

                    if user_input.lower() == "y":
                        if not storing_avg_heartrate:
                            print("No heart rate data collected.")
                            continue

                        current_avg = sum(storing_avg_heartrate) / len(storing_avg_heartrate) if values else 0
                        print("AVG HEARRATES", storing_avg_heartrate)
                        print(f"Current avg heart rate: {round(current_avg, 2)}")

                        if current_avg > previous_avg:
                            positive_indicators()
                        else:
                            negative_indicators()

                        previous_avg = current_avg
                        storing_avg_heartrate = []

                        continue
                   
                    time.sleep(2)

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
