from flask import Flask, render_template_string, request, redirect, session
import mysql.connector
import os
import random
import matplotlib
matplotlib.use('Agg')   # 🔥 FIX

import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "atm_secret"

# ---------------- DATABASE ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="M@nsi120",
    database="atm_db"
)
cursor = db.cursor(dictionary=True)

# ---------------- LOGIN UI ----------------
login_page = """
<!DOCTYPE html>
<html>
<head>
<title>ATM Login</title>
<style>
body {
    font-family: Arial;
    background: linear-gradient(135deg, #667eea, #764ba2);
    display:flex; justify-content:center; align-items:center;
    height:100vh;
}
.box {
    background:white;
    padding:30px;
    border-radius:10px;
    text-align:center;
}
input,button {
    padding:10px; margin:10px;
}
button {background:#667eea;color:white;border:none;}
</style>
</head>
<body>
<div class="box">
<h2>🏧 ATM Login</h2>
<form method="POST">
<input type="password" name="pin" placeholder="Enter PIN" required><br>
<button>Login</button>
</form>
<p style="color:red;">{{msg}}</p>
</div>
</body>
</html>
"""

# ---------------- DASHBOARD UI ----------------
dashboard_page = """
<!DOCTYPE html>
<html>
<head>
<title>Bank Dashboard</title>
<style>
body {margin:0; font-family:Arial; background:#f4f6f9;}
.sidebar {
    width:200px; background:#2c3e50; color:white;
    position:fixed; height:100%; padding:20px;
}
.sidebar a {
    color:white; display:block; margin:10px 0;
    text-decoration:none;
}
.main {margin-left:220px; padding:20px;}
.card {
    display:inline-block; width:30%;
    padding:20px; margin:10px;
    border-radius:10px; color:white;
}
.balance {background:#3498db;}
.deposit {background:#2ecc71;}
.withdraw {background:#e74c3c;}
.form-box {background:white;padding:20px;border-radius:10px;}
button {padding:10px;margin:10px;}
.msg {color:green;}
.err {color:red;}
</style>
</head>

<body>

<div class="sidebar">
<h2>🏦 MyBank</h2>
<a href="/dashboard">Dashboard</a>
<a href="/history">Transactions</a>
<a href="/analytics">Analytics</a>
<a href="/logout">Logout</a>
</div>

<div class="main">

<h2>Welcome {{name}} 👋</h2>

<div class="card balance">
<h3>Balance</h3>
₹{{balance}}
</div>

<div class="card deposit">Deposit</div>
<div class="card withdraw">Withdraw</div>

<div class="form-box">
<form method="POST">
<input type="number" name="amount" placeholder="Enter amount" required>
<input type="text" name="target_pin" placeholder="Transfer PIN"><br>

<button name="action" value="deposit">Deposit</button>
<button name="action" value="withdraw">Withdraw</button>
<button name="action" value="transfer">Transfer</button>
</form>

<p class="msg">{{msg}}</p>
<p class="err">{{err}}</p>

</div>

</div>
</body>
</html>
"""

# ---------------- HELPER ----------------
def log_transaction(uid, t, amt):
    cursor.execute(
        "INSERT INTO transactions (user_id,type,amount) VALUES (%s,%s,%s)",
        (uid, t, amt)
    )
    db.commit()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        pin=request.form["pin"]
        cursor.execute("SELECT * FROM users WHERE pin=%s",(pin,))
        user=cursor.fetchone()

        if user:
            session["user"]=user["id"]
            return redirect("/dashboard")
        else:
            msg="Invalid PIN ❌"

    return render_template_string(login_page,msg=msg)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    uid=session["user"]

    cursor.execute("SELECT * FROM users WHERE id=%s",(uid,))
    user=cursor.fetchone()

    msg=""
    err=""

    if request.method=="POST":
        action=request.form["action"]
        amount=float(request.form["amount"])

        if action=="deposit":
            cursor.execute("UPDATE users SET balance=balance+%s WHERE id=%s",(amount,uid))
            db.commit()
            log_transaction(uid,"Deposit",amount)
            msg="Deposit Successful ✅"

        elif action=="withdraw":
            if amount<=user["balance"]:
                cursor.execute("UPDATE users SET balance=balance-%s WHERE id=%s",(amount,uid))
                db.commit()
                log_transaction(uid,"Withdraw",amount)
                msg="Withdraw Successful ✅"
            else:
                err="Insufficient Balance ❌"

        elif action=="transfer":
            target_pin=request.form["target_pin"]

            # OTP GENERATION
            otp=random.randint(1000,9999)
            session["otp"]=otp
            session["amount"]=amount
            session["target"]=target_pin

            print("OTP:",otp)  # console

            return redirect("/verify")

    return render_template_string(dashboard_page,name=user["name"],balance=user["balance"],msg=msg,err=err)

# ---------------- OTP VERIFY ----------------
@app.route("/verify", methods=["GET","POST"])
def verify():
    if request.method=="POST":
        entered=int(request.form["otp"])

        if entered==session.get("otp"):
            uid=session["user"]
            amt=session["amount"]
            target_pin=session["target"]

            cursor.execute("SELECT * FROM users WHERE pin=%s",(target_pin,))
            target=cursor.fetchone()

            cursor.execute("SELECT * FROM users WHERE id=%s",(uid,))
            user=cursor.fetchone()

            if target and amt<=user["balance"]:
                cursor.execute("UPDATE users SET balance=balance-%s WHERE id=%s",(amt,uid))
                cursor.execute("UPDATE users SET balance=balance+%s WHERE id=%s",(amt,target["id"]))
                db.commit()

                log_transaction(uid,"Transfer Sent",amt)
                log_transaction(target["id"],"Transfer Received",amt)

                return "Transfer Successful ✅ <br><a href='/dashboard'>Back</a>"
            else:
                return "Transfer Failed ❌"

        else:
            return "Wrong OTP ❌"

    return """
    <h2>Enter OTP</h2>
    <form method="POST">
    <input name="otp">
    <button>Verify</button>
    </form>
    """

# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/")

    uid=session["user"]

    cursor.execute("SELECT * FROM transactions WHERE user_id=%s",(uid,))
    data=cursor.fetchall()

    return render_template_string("""
    <h2>Transaction History</h2>
    <table border=1>
    <tr><th>Type</th><th>Amount</th><th>Date</th></tr>
    {% for t in data %}
    <tr><td>{{t.type}}</td><td>{{t.amount}}</td><td>{{t.date}}</td></tr>
    {% endfor %}
    </table>
    <a href="/dashboard">Back</a>
    """,data=data)

# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/")

    uid=session["user"]

    cursor.execute("SELECT type,SUM(amount) as total FROM transactions WHERE user_id=%s GROUP BY type",(uid,))
    data=cursor.fetchall()

    labels=[x["type"] for x in data]
    values=[x["total"] for x in data]

    plt.figure()
    plt.pie(values,labels=labels,autopct='%1.1f%%')

    if not os.path.exists("static"):
        os.makedirs("static")

    path="static/chart.png"
    plt.savefig(path)
    plt.close()

    return f"""
    <h2>Analytics</h2>
    <img src="/{path}" width="400">
    <br><a href="/dashboard">Back</a>
    """

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(debug=True)