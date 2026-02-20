from flask import Flask, jsonify, render_template_string, request, redirect, session
from blockchain import Blockchain, GovernmentProject, Contractor
from sklearn.ensemble import IsolationForest
import numpy as np

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------------
# GLOBAL SYSTEM STORAGE
# ---------------------------
blockchain = Blockchain()

projects = {}
contractors = {}
payment_history = {}

# ---------------------------
# USERS
# ---------------------------
users = {
    "gov": {"password": "gov123", "role": "government"},
    "contractor": {"password": "contract123", "role": "contractor"},
    "public": {"password": "public123", "role": "public"}
}

# ---------------------------
# FRAUD DETECTION
# ---------------------------
def detect_fraud(project_id):
    history = payment_history.get(project_id, [])

    if len(history) < 5:
        return False

    data = np.array(history).reshape(-1, 1)
    model = IsolationForest(contamination=0.2, random_state=42)
    model.fit(data)

    predictions = model.predict(data)

    return predictions[-1] == -1


# ---------------------------
# LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])

def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username]["password"] == password:
            session["role"] = users[username]["role"]
            return redirect("/")
        else:
            return "Invalid credentials"

    return """
        <h2>Login</h2>
        <form method="POST">
            Username: <input name="username"><br><br>
            Password: <input type="password" name="password"><br><br>
            <button type="submit">Login</button>
        </form>
    """

@app.route("/logout")
def logout():
    session.pop("role", None)
    return redirect("/login")

# ---------------------------
# CREATE PROJECT (Government Only)
# ---------------------------
@app.route("/create_project", methods=["GET", "POST"])
def create_project():
    if session.get("role") != "government":
        return "Unauthorized"

    if request.method == "POST":
        project_id = request.form["project_id"]
        name = request.form["name"]
        budget = float(request.form["budget"])
        contractor_name = request.form["contractor"]

        project = GovernmentProject(project_id, name, budget)
        contractor = Contractor(project_id, contractor_name)

        projects[project_id] = project
        contractors[project_id] = contractor
        payment_history[project_id] = []

        blockchain.add_block({
            "action": "Project Created",
            "project_id": project_id,
            "name": name,
            "budget": budget,
            "contractor": contractor_name
        })

        return redirect("/")

    return """
        <h2>Create New Project</h2>
        <form method="POST">
            Project ID: <input name="project_id"><br><br>
            Project Name: <input name="name"><br><br>
            Budget: <input name="budget"><br><br>
            Contractor Name: <input name="contractor"><br><br>
            <button type="submit">Create</button>
        </form>
    """

# ---------------------------
# RELEASE FUNDS
# ---------------------------


@app.route("/release/<project_id>")
def release(project_id):
    if session.get("role") != "government":
        return "Unauthorized"

    project = projects.get(project_id)
    contractor = contractors.get(project_id)

    if not project:
        return "Project not found"

    # Find next pending milestone
    for milestone in project.milestones:
        if milestone not in project.completed_milestones:
            amount = project.release_funds(milestone)

            if isinstance(amount, float):
                contractor.receive_funds(amount)

                blockchain.add_block({
                    "action": "Milestone Completed",
                    "project_id": project_id,
                    "milestone": milestone,
                    "released_amount": amount,
                    "contractor_balance": contractor.balance
                })

            break  # Stop after one milestone release
    else:
        return "All milestones already completed."

    return redirect("/")


# ---------------------------
# CONTRACTOR PAYMENT
# ---------------------------
@app.route("/pay/<project_id>", methods=["GET", "POST"])
def pay(project_id):
    if session.get("role") != "contractor":
        return "Unauthorized"

    contractor = contractors.get(project_id)

    if request.method == "POST":
        recipient = request.form["recipient"]
        amount = float(request.form["amount"])

        payment = contractor.make_payment(recipient, amount)

        if isinstance(payment, dict):
            payment_history[project_id].append(amount)

            blockchain.add_block({
                "action": "Contractor Payment",
                "project_id": project_id,
                "details": payment,
                "remaining_balance": contractor.balance
            })

            if detect_fraud(project_id):
                blockchain.add_block({
                    "action": "⚠️ Fraud Alert",
                    "project_id": project_id,
                    "amount": amount
                })

        return redirect("/")

    return f"""
        <h2>Make Payment for Project {project_id}</h2>
        <form method="POST">
            Recipient: <input name="recipient"><br><br>
            Amount: <input name="amount"><br><br>
            <button type="submit">Pay</button>
        </form>
    """

# ---------------------------
# HOME DASHBOARD
# ---------------------------

@app.route("/")
def home():
    if "role" not in session:
        return redirect("/login")

    role = session["role"]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Transparency Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f9;
                margin: 0;
                padding: 0;
            }

            header {
                background: #1e3a8a;
                color: white;
                padding: 20px;
                text-align: center;
            }

            .container {
                padding: 30px;
            }

            .card {
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }

            .btn {
                display: inline-block;
                padding: 8px 14px;
                margin-top: 10px;
                border-radius: 5px;
                text-decoration: none;
                color: white;
                font-size: 14px;
            }

            .btn-blue { background: #2563eb; }
            .btn-green { background: #16a34a; }
            .btn-red { background: #dc2626; }

            .btn:hover {
                opacity: 0.9;
            }

            .ledger {
                background: #111827;
                color: #e5e7eb;
                padding: 15px;
                border-radius: 10px;
                max-height: 300px;
                overflow-y: auto;
                font-size: 13px;
            }

            footer {
                text-align: center;
                padding: 15px;
                background: #1e3a8a;
                color: white;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>

        <header>
            <h1>National Public Fund Transparency System</h1>
            <p>Logged in as: <strong>{{role}}</strong></p>
            <a href="/logout" class="btn btn-red">Logout</a>
        </header>

        <div class="container">

            {% if role == "government" %}
                <div class="card">
                    <h2>Government Controls</h2>
                    <a href="/create_project" class="btn btn-blue">Create New Project</a>
                </div>
            {% endif %}

            <h2>Active Projects</h2>

            {% for pid, proj in projects.items() %}
                <div class="card">
                    <h3>{{proj.project_name}} ({{pid}})</h3>
                    <p><strong>Total Budget:</strong> ₹{{proj.total_budget}}</p>
                    <p><strong>Released:</strong> ₹{{proj.released_amount}}</p>

                    {% if role == "government" %}
                        <a href="/release/{{pid}}" class="btn btn-green">Release Milestone</a>
                    {% endif %}

                    {% if role == "contractor" %}
                        <a href="/pay/{{pid}}" class="btn btn-blue">Make Payment</a>
                    {% endif %}
                </div>
            {% endfor %}

            <h2>Blockchain Ledger</h2>
            <div class="ledger">
                {% for block in chain %}
                    <p>
                        <strong>Block {{block.index}}</strong> → {{block.data}}
                    </p>
                {% endfor %}
            </div>

        </div>

        <footer>
            © 2026 Government Transparency Blockchain Prototype
        </footer>

    </body>
    </html>
    """

    return render_template_string(
        html,
        projects=projects,
        chain=blockchain.chain,
        role=role
    )


# ---------------------------
# VALIDATE
# ---------------------------
@app.route("/validate")
def validate():
    return jsonify({"Blockchain Valid": blockchain.is_chain_valid()})


if __name__ == "__main__":
    app.run(debug=True)
