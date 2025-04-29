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

app = Flask(__name__)
app.secret_key = os.environ.get(
    "AI_VIDEO_SUMMARIZER_SECURITY_KEY"
)  # Needed for session

openai.api_key = os.environ.get("OPENAI_API_KEY")
os.makedirs("./static/processed/", exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = validate_user(username, password)
        if user:
            session["logged_in"] = True
            return redirect(url_for("upload_videos"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/upload", methods=["GET", "POST"])
def upload_videos():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        video1 = request.files["video1"]
        video2 = request.files["video2"]

        text_list1, temp_path1, clips1 = save_and_process_video(video1)
        text_list2, temp_path2, clips2 = save_and_process_video(video2)

        text1 = " ".join(text_list1)
        text2 = " ".join(text_list2)

        best_clips_output_path = select_and_combine_best_clips(
            text_list1, text_list2, clips1, clips2
        )

        summary_prompt = prepare_prompt(
            "input/summary_prompt.txt", text1, text2, "summary_prompt.txt"
        )

        try:
            cleaned_summary_content = call_openai_api(
                summary_prompt, "summary_result.json"
            )
            summary_output_json = json.loads(cleaned_summary_content)

            best_video = video1 if summary_output_json.get("bestText") == 1 else video2
            best_path = os.path.join("static/processed/", best_video.filename)
            shutil.move(temp_path1 if best_video == video1 else temp_path2, best_path)

            for lang, summary in summary_output_json.get("summary", {}).items():
                summary_output_json["summary"][lang] = html.unescape(summary)

            return render_template(
                "output.html",
                data=summary_output_json,
                video_path=best_path,
                best_clips_output_path=best_clips_output_path,
            )

        except Exception as e:
            traceback.print_exc()
            return f"Error: {str(e)}<br><pre>{traceback.format_exc()}</pre>"

    return render_template("upload.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
