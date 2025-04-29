# Import necessary libraries
import os
import tempfile
import json
import openai
import mysql.connector
from speech_to_text import process_video
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Database configuration for connecting to MySQL
db_config = {
    "host": "localhost",
    "port": "8111",
    "user": "root",
    "password": "",  # Update with actual password if required
    "database": "ai_video_summarizer",
}


# Function to validate user credentials from database
def validate_user(username, password):
    conn = mysql.connector.connect(**db_config)  # Connect to database
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s", (username, password)
    )
    user = cursor.fetchone()  # Fetch user if credentials match
    conn.close()
    return user


# Function to save uploaded video file and process it (split + transcribe)
def save_and_process_video(file):
    temp_dir = tempfile.mkdtemp()  # Create a temporary directory
    temp_path = os.path.join(temp_dir, file.filename)  # Define temporary path
    file.save(temp_path)  # Save uploaded file to temp path
    text_list, clips = process_video(temp_path, temp_dir)  # Process video
    return temp_dir, text_list, temp_path, clips  # Return extracted text list, path, and clip paths


# Function to prepare prompt by replacing placeholders with actual extracted text
def prepare_prompt(prompt_file_path, text1, text2, output_filename):
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    # Replace placeholders with actual extracted text
    prompt = prompt.replace("<TEXT1>", text1).replace("<TEXT2>", text2)

    # Save the prepared prompt for record
    with open(
            "./static/processed/{}".format(output_filename), "w", encoding="utf-8"
    ) as out:
        out.write(prompt)
    return prompt  # Return the prepared prompt


# Function to call OpenAI's API with the given prompt and save response
def call_openai_api(prompt, filename):
    response = openai.chat.completions.create(
        model="gpt-4o",  # Using the 'gpt-4o' model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Low randomness for more factual answers
        max_tokens=2000,  # Max length of response
    )
    content = response.choices[0].message.content.strip("`").strip()

    # If response starts with "json", strip it
    if content.startswith("json"):
        content = content[4:].strip()

    json_data = json.loads(content)  # Parse JSON
    # Save the JSON response for reference
    with open("./static/processed/{}".format(filename), "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)
    return content  # Return the raw content


# Function to combine multiple video clips into a single video
def combine_videos(video_paths, output_path):
    try:
        # Load all video clips
        clips = [VideoFileClip(path) for path in video_paths]

        # Concatenate the clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Save the final combined video
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        print(f"Videos successfully combined into '{output_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to select the best clips from two videos and combine them
def select_and_combine_best_clips(text_list1, text_list2, clips1, clips2):
    # Prepare a new prompt for selecting best clips based on text
    text_sampling_prompt = prepare_prompt(
        "input/text_sampling_prompt.txt",
        str(text_list1),
        str(text_list2),
        "summary_prompt.txt",
    )

    # Call OpenAI to process and find best clips
    cleaned_sampling_content = call_openai_api(
        text_sampling_prompt, "text_sampling_result.json"
    )
    sampling_output_json = json.loads(cleaned_sampling_content)

    # Select best clips from the first video based on OpenAI output
    best_clips_from_video1 = [
        clip_path
        for index, clip_path in enumerate(clips1)
        if index in sampling_output_json.get("video1")
    ]

    # Select best clips from the second video based on OpenAI output
    best_clips_from_video2 = [
        clip_path
        for index, clip_path in enumerate(clips2)
        if index in sampling_output_json.get("video2")
    ]

    # Define output path for combined best clips
    best_clips_output_path = "./static/processed/best_clips.mp4"
    best_clips_path = best_clips_from_video1 + best_clips_from_video2

    # Combine selected best clips into a single video
    combine_videos(best_clips_path, best_clips_output_path)
    return best_clips_output_path  # Return the path of the final combined video
