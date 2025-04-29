# Import necessary libraries
import moviepy.editor as mp
import speech_recognition as sr
import os

# Function to split a video into smaller clips of a given interval (default 30 seconds)
def split_video(video_path, output_dir, interval=30):
    clip = mp.VideoFileClip(video_path)  # Load the video
    duration = int(clip.duration)  # Get total duration in seconds

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    clips = []
    # Split video into subclips
    for start in range(0, duration, interval):
        end = min(start + interval, duration)
        subclip = clip.subclip(start, end)  # Extract subclip
        output_path = os.path.join(output_dir, f"clip_{start}_{end}.mp4")
        print(output_path)  # Print output path for debugging
        subclip.write_videofile(
            output_path, codec="libx264", audio_codec="aac", logger=None
        )
        clips.append(output_path)  # Store the path of created clip

    clip.close()  # Close the original video to free memory
    return clips  # Return list of clip file paths

# Function to extract audio from a video file
def extract_audio(video_path, audio_path):
    clip = mp.VideoFileClip(video_path)  # Load the video
    clip.audio.write_audiofile(audio_path, logger=None)  # Save audio to a file
    clip.close()  # Close the clip after extraction
    return audio_path  # Return the path to the saved audio file

# Function to transcribe the extracted audio to text
def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()  # Initialize recognizer
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)  # Record the audio from the file
        try:
            text = recognizer.recognize_google(audio)  # Use Google API to recognize speech
            return text
        except sr.UnknownValueError:
            # If speech is unintelligible
            return "Speech not recognized"
        except sr.RequestError as e:
            # If API request fails
            return f"Request error: {e}"

# Function to fully process a video: split into clips, extract audio, and transcribe
def process_video(video_path, temp_dir):
    print(video_path)  # Print video path for debugging
    results = []
    clips = split_video(video_path, temp_dir)  # Split video into clips

    for clip_path in clips:
        audio_path = clip_path.replace(".mp4", ".wav")  # Define audio path from clip path
        extract_audio(clip_path, audio_path)  # Extract audio from clip
        text = transcribe_audio(audio_path)  # Transcribe extracted audio
        results.append(text)  # Store transcription result

    return results, clips  # Return list of transcribed texts and clips
