import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def main():
    return render_template("index.html")

@app.route("/viz")
def cwhoiviz():
    return "<i>uweeheehee</i><br/><p>my riddles three...</p>"
