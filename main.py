
import random
import json
from string import ascii_uppercase
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import requests

app = Flask(__name__)
app.config["SECRET_KEY"] = "123456"

socketio = SocketIO(app, cors_allowed_origins="*")
rooms = {}




# CREATING ROOMS WITH RESERVED ROOM CODES
rooms_url = "https://getpantry.cloud/apiv1/pantry/8fd2020c-eda8-4db2-bff3-6eb92f3dbcc1/basket/reserved-room-codes"
response = requests.request("GET", rooms_url, timeout=10)

reserved_codes_JSON = json.loads(response.text)
reserved_codes_ARRAY = reserved_codes_JSON["code"]

for i in range(0, len(reserved_codes_ARRAY)):
    rooms[reserved_codes_ARRAY[i]] = {"members": 0, "messages": []}





# FUNCTION WHICH WILL GENERATE [lenght]-DIGIT RANDOM CODE
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

# FUNCTION WHICH WILL GIVE IP ADDRESS OF CLIENT
def get_ip():
    response = requests.get('https://api64.ipify.org?format=json', timeout=5).json()
    return response["ip"]


# FUNCTION WHICH WILL GIVE ALL DETAILS OF THE CLIENT
def get_user_details():
    user_details = requests.get(f'https://api.ipdata.co?api-key=0d76c3e1fb21d37c45caa78c4fe5e53d05ec75fe37be4813b79e00ce', timeout=5).json()
    return user_details

def pantrydb_put(unique_id, value, url):
    payload = json.dumps({
        unique_id: value
    })
    headers = {"Content-Type": "application/json"}
    response = requests.request("PUT", url, headers=headers, data=payload)


# IF SOMEONE BY MISTAKE GIVES UNKNOWN ARG
@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return redirect(url_for("/"))

# ROOT DIR OF WEBSITE
@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template(
                "home.html", error="Please enter a name.", code=code, name=name
            )

        if join != False and not code:
            return render_template(
                "home.html", error="Please enter a room code.", code=code, name=name
            )

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template(
                "home.html", error="Room does not exist.", code=code, name=name
            )

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")

# ROOM ROUTE
@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send(
        {
            "name": "",
            "message": """<i class="fas fa-map-pin"></i>&nbsp; <b>"""
            + name
            + "</b><i> joined"
            + """</i>""",
        },
        to=room,
    )
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

    # print(rooms)



@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:

        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            print(room)
            if room in reserved_codes_ARRAY:
                print("Can't Delete Room, it is registered under reserved rooms")
            else:
                del rooms[room]

    send({"name": "", "message": """<i class="fas fa-map-pin"></i>&nbsp; <b>""" + name + "</b><i> left" + """</i>"""},to=room,)
    print(f"{name} has left the room {room}")

    print(rooms)


if __name__ == "__main__":
    socketio.run(app, debug=True)
