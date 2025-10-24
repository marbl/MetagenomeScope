__version__ = "0.1.0-dev"

import os
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def main():
    return render_template("index.html")
