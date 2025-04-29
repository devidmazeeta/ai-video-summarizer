# Import necessary libraries
import os
import json
import shutil
import traceback
import html
from flask import Flask, request, render_template, redirect, url_for, session
import openai
from utils import (
    validate_user,
    save_and_process_video,
    prepare_prompt,
    call_openai_api,
    select_and_combine_best_clips,
)

# Initialize the Flask application
app = Flask(__name__)
# Set the secret key for session management
app.secret_key = os.environ.get("AI_VIDEO_SUMMARIZER_SECURITY_KEY")

# Set OpenAI API key for making API calls
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Ensure the directory for processed videos exists
os.makedirs("./static/processed/", exist_ok=True)


# Route for login page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get username and password from the login form
        username = request.form.get("username")
        password = request.form.get("password")

        # Validate user credentials
        user = validate_user(username, password)
        if user:
            # If valid, create a login session
            session["logged_in"] = True
            return redirect(url_for("upload_videos"))
        # If invalid, show login page with error
        return render_template("login.html", error="Invalid credentials")

    # GET request: just render the login page
    return render_template("login.html")


# Route for uploading videos
@app.route("/upload", methods=["GET", "POST"])
def upload_videos():
    # If user not logged in, redirect to login
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        # Get uploaded video files from form
        video1 = request.files["video1"]
        video2 = request.files["video2"]

        # Save videos temporarily and extract text and clips
        text_list1, temp_path1, clips1 = save_and_process_video(video1)
        text_list2, temp_path2, clips2 = save_and_process_video(video2)

        # Combine text extracted from both videos
        text1 = " ".join(text_list1)
        text2 = " ".join(text_list2)

        # Select and combine best clips from both videos
        best_clips_output_path = select_and_combine_best_clips(
            text_list1, text_list2, clips1, clips2
        )

        # Prepare prompt for OpenAI API to generate summary
        summary_prompt = prepare_prompt(
            "input/summary_prompt.txt", text1, text2, "summary_prompt.txt"
        )

        try:
            # Call OpenAI API to get summary
            cleaned_summary_content = call_openai_api(
                summary_prompt, "summary_result.json"
            )
            summary_output_json = json.loads(cleaned_summary_content)

            # Determine which video is best based on API response
            best_video = video1 if summary_output_json.get("bestText") == 1 else video2
            best_path = os.path.join("static/processed/", best_video.filename)

            # Move the best video's temporary file to a permanent location
            shutil.move(temp_path1 if best_video == video1 else temp_path2, best_path)

            # Unescape any HTML entities in the summary text
            for lang, summary in summary_output_json.get("summary", {}).items():
                summary_output_json["summary"][lang] = html.unescape(summary)

            # Render output page with summary and video paths
            return render_template(
                "output.html",
                data=summary_output_json,
                video_path=best_path,
                best_clips_output_path=best_clips_output_path,
            )

        except Exception as e:
            # In case of error, print traceback and display error message
            traceback.print_exc()
            return f"Error: {str(e)}<br><pre>{traceback.format_exc()}</pre>"

    # GET request: just render the upload page
    return render_template("upload.html")


# Route for logging out
@app.route("/logout")
def logout():
    # Clear the session and redirect to login page
    session.clear()
    return redirect(url_for("login"))


# Main entry point of the app
if __name__ == "__main__":
    app.run(debug=True)
