from flask import Flask, request
import os
import re
import json

app = Flask(__name__)

stories = [
    {"text": ["zero", "zero", "zero"], "spans": [[1, 10, 11]]},
    {"text": "one", "spans": [[1, 10, 11]]},
]


@app.route("/text")
def text():
    try:
        user = request.args["user"]
        story_number = int(request.args["storyNumber"])
        return json.dumps(stories[story_number])

    except Exception as e:
        return json.dumps(f"request failed: {e}")


@app.route("/login")
def login():
    return "Hiiiiiiiiii"


@app.route("/grade")
def grade():
    pass


if __name__ == "__main__":
    try:
        PORT = os.environ["REST_PORT"]
    except Exception as e:
        print(e)
        print(
            "Unable to start, please set port for rest API through envoronment 'REST_PORT'"
        )
        exit(1)

    print(f"Starting server on port {PORT}")
    app.run(debug=True, host="0.0.0.0", port=PORT)
