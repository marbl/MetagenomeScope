from flask import Flask

app = Flask("MgSc")

@app.route("/")
def main():
    return "<b>oaisdfijowiw</b"

@app.route("/viz")
def cwhoiviz():
    return "<i>uweeheehee</i><br/><p>my riddles three...</p>"
