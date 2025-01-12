import random
from string import ascii_uppercase
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "123456"

socketio = SocketIO(app, cors_allowed_origins="*")
rooms = {}


# FUNCTION WHICH WILL GENERATE [lenght]-DIGIT RANDOM CODE
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code


# IF SOMEONE BY MISTAKE GIVES UNKNOWN ARG
# @app.errorhandler(404)
# def page_not_found(e):
#     return redirect(url_for("home"))


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

    content = {
        "name": session.get("name"),
        "message": data["data"],
        "dtime": data["time"],
    }
    send(content, to=room)

    # SAVING MESSAGE IN ARRAY
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
            "message": f"""[+] <b>{name}</b> """ + " joined",
            "dtime": "Just Now"
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
            del rooms[room]

    send(
        {
            "name": "",
            "message": f"""[-] <b>{name}</b> """+" left",
            "dtime": "Just Now"
        },
        to=room,
    )
    print(f"{name} has left the room {room}")

    print(rooms)


if __name__ == "__main__":
    socketio.run(app, debug=True)
