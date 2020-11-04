from flask import Flask
import os

app = Flask(__name__)


@app.route("/text")
def text():
    return "the text"


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
