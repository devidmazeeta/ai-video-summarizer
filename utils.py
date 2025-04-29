import os
import tempfile
import json
import openai
import mysql.connector
from speech_to_text import process_video
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Database configuration
db_config = {
    "host": "localhost",
    "port": "8111",
    "user": "root",
    "password": "",  # update if needed
    "database": "ai_video_summarizer",
}


def validate_user(username, password):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s", (username, password)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def save_and_process_video(file):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    text_list, clips = process_video(temp_path, temp_dir)
    return text_list, temp_path, clips


def prepare_prompt(prompt_file_path, text1, text2, output_filename):
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    prompt = prompt.replace("<TEXT1>", text1).replace("<TEXT2>", text2)
    with open(
        "./static/processed/{}".format(output_filename), "w", encoding="utf-8"
    ) as out:
        out.write(prompt)
    return prompt


def call_openai_api(prompt, filename):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    content = response.choices[0].message.content.strip("`").strip()
    if content.startswith("json"):
        content = content[4:].strip()
    json_data = json.loads(content)
    with open("./static/processed/{}".format(filename), "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)
    return content


def combine_videos(video_paths, output_path):
    try:
        # Load video clips
        clips = [VideoFileClip(path) for path in video_paths]

        # Combine video clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the result to the output file
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        print(f"Videos successfully combined into '{output_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")


def select_and_combine_best_clips(text_list1, text_list2, clips1, clips2):
    text_sampling_prompt = prepare_prompt(
        "input/text_sampling_prompt.txt",
        str(text_list1),
        str(text_list2),
        "summary_prompt.txt",
    )

    cleaned_sampling_content = call_openai_api(
        text_sampling_prompt, "text_sampling_result.json"
    )
    sampling_output_json = json.loads(cleaned_sampling_content)

    best_clips_from_video1 = [
        clip_path
        for index, clip_path in enumerate(clips1)
        if index in sampling_output_json.get("video1")
    ]

    best_clips_from_video2 = [
        clip_path
        for index, clip_path in enumerate(clips2)
        if index in sampling_output_json.get("video2")
    ]

    best_clips_output_path = "./static/processed/best_clips.mp4"
    best_clips_path = best_clips_from_video1 + best_clips_from_video2
    combine_videos(best_clips_path, best_clips_output_path)
    return best_clips_output_path
