import moviepy.editor as mp
import speech_recognition as sr
import os


def split_video(video_path, output_dir, interval=30):
    clip = mp.VideoFileClip(video_path)
    duration = int(clip.duration)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    clips = []
    for start in range(0, duration, interval):
        end = min(start + interval, duration)
        subclip = clip.subclip(start, end)
        output_path = os.path.join(output_dir, f"clip_{start}_{end}.mp4")
        print(output_path)
        subclip.write_videofile(
            output_path, codec="libx264", audio_codec="aac", logger=None
        )
        clips.append(output_path)

    clip.close()  # <-- CLOSE the original clip
    return clips


def extract_audio(video_path, audio_path):
    clip = mp.VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path, logger=None)
    clip.close()  # <-- CLOSE after extracting
    return audio_path


def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Speech not recognized"
        except sr.RequestError as e:
            return f"Request error: {e}"


def process_video(video_path, temp_dir):
    print(video_path)
    results = []
    clips = split_video(video_path, temp_dir)
    for clip_path in clips:
        audio_path = clip_path.replace(".mp4", ".wav")
        extract_audio(clip_path, audio_path)
        text = transcribe_audio(audio_path)
        results.append(text)

    return results, clips
