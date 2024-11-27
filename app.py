from flask import Flask, request, jsonify
from moviepy.editor import ImageClip, concatenate_videoclips
from google.cloud import storage
import openai
import os
import uuid
import requests

# Initialize Flask app
app = Flask(__name__)

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Video generation settings
OUTPUT_VIDEO_PATH = "/tmp/output_video.mp4"
FPS = 24
DURATION_PER_IMAGE = 5  # seconds

def debug_tmp_files():
    for filename in os.listdir("/tmp"):
        file_path = os.path.join("/tmp", filename)
        if os.path.isfile(file_path):
            print(f"File: {filename}, Size: {os.path.getsize(file_path)} bytes")

def upload_to_gcs(local_path, bucket_name, blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to gs://{bucket_name}/{blob_name}")

def upload_tmp_files(bucket_name):
    for filename in os.listdir("/tmp"):
        local_path = os.path.join("/tmp", filename)
        blob_name = f"tmp-files/{filename}"  # Organize in a folder in GCS
        upload_to_gcs(local_path, bucket_name, blob_name)

def log_tmp_directory():
    print("Contents of /tmp:")
    for filename in os.listdir("/tmp"):
        print(filename)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        # Receive the text paragraph
        data = request.json
        if not data or "paragraph" not in data:
            return jsonify({"error": "Please provide a paragraph in the request"}), 400

        paragraph = data['paragraph']
        sentences = paragraph.split(".")  # Split into sentences for image prompts

        # Generate images for each sentence
        images = []
        for sentence in sentences:
            if sentence.strip():  # Ignore empty sentences
                response = openai.Image.create(
                    prompt=sentence.strip(),
                    n=1,
                    size="1024x1024"
                )
                print(response)
                image_url = response['data'][0]['url']
                print(image_url)
                images.append(image_url)

        downloaded_images = []

        # Download images
        for i, image_url in enumerate(images):
            image_path = f"/tmp/image_{i}.png"
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                with open(image_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                downloaded_images.append(image_path)
            else:
                raise Exception(f"Failed to download image: {image_url}")

        # Create video clips from images
        clips = []
        for image_path in downloaded_images:
            clip = ImageClip(image_path, duration=DURATION_PER_IMAGE)
            clips.append(clip)

        # Concatenate clips into a single video
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(OUTPUT_VIDEO_PATH, fps=FPS)
        
        log_tmp_directory()
        upload_tmp_files("videoai-ade")
        debug_tmp_files()

        # Serve the video path
        return jsonify({"video_url": f"{OUTPUT_VIDEO_PATH}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
