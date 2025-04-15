import os
import json
import tempfile
# from google.oauth2 import service_account
import vertexai


def init_vertexai():
    """Initialize Google Vertex AI with service account credentials on Render."""
    try:
        # 1️⃣ Get the JSON string from environment variable
        credentials_json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if not credentials_json_str:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set.")

        # 2️⃣ Parse the JSON string
        try:
            credentials_json = json.loads(credentials_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

        # 3️⃣ Ensure the 'private_key' is present
        if "private_key" not in credentials_json:
            raise ValueError("Missing 'private_key' in GOOGLE_APPLICATION_CREDENTIALS_JSON.")

        # 4️⃣ Write credentials to a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            json.dump(credentials_json, temp_file)
            temp_credentials_path = temp_file.name

        print(f"✅ Credentials stored in temporary file: {temp_credentials_path}")

        # 5️⃣ Set GOOGLE_APPLICATION_CREDENTIALS to use this file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_credentials_path

        # 6️⃣ Retrieve Google Cloud project details
        project_id = os.environ.get("PROJECT_ID")
        location = os.environ.get("LOCATION", "us-central1")
        if not project_id:
            raise ValueError("PROJECT_ID environment variable not set.")

        # 7️⃣ Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        print(f"✅ Successfully initialized Vertex AI for project: {project_id} (Region: {location})")
       
        return True

    except Exception as e:
        print(f"🚨 Error initializing Vertex AI: {e}")
        return False
