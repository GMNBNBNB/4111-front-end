import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# connect to DB
DATABASEURI = "postgresql://mg4774:177624@104.196.222.236/proj1part2"

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print("error when connect db")
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/usersList')
def users():
    cursor = g.conn.execute(text("SELECT * FROM users"))
    users = []
    for row in cursor:
        users.append(row)
    cursor.close()
    return render_template("userList.html", users=users)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        nickname = request.form['nickname']
        join_date = request.form['join_date']
        try:
            g.conn.execute(
                text("INSERT INTO Users (username, nickname, join_date) VALUES (:username, :nickname, :join_date)"),
                {"username": username, "nickname": nickname, "join_date": join_date}
            )
            g.conn.commit()
            return redirect('/index')
        except Exception as e:
            return f"add user failure: {e}"
    return render_template("add_user.html")

@app.route('/delete_user/<username>')
def delete_user(username):
    try:
        g.conn.execute(text("DELETE FROM Users WHERE username = :username"), {"username": username})
        g.conn.commit()
        return redirect('/users')
    except Exception as e:
        return f"error: {e}"
    
@app.route('/test_db')
def test_db():
    if not g.conn:
        return "cant connect to db", 500
    try:
        cursor = g.conn.execute(text("SELECT * FROM users"))
        users = []
        for row in cursor:
          users.append(row)
        cursor.close()
        return f"db connect successfully result is: {users}"
    except Exception as e:
        return f"check failure: {e}", 500


if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        HOST, PORT = host, port
        print(f"run at {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
