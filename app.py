from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
import json, os
from datetime import datetime, timedelta
import random
import openai

app = Flask(__name__)
DATA_FILE = "tasks.json"
PROFILE_FILE = "profile.json"
SEARCH_FILE = "searches.json"

# OpenAI key read from environment variable (optional)
openai.api_key = os.getenv("OPENAI_API_KEY")

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def next_id(items):
    if not items: return 1
    return max(i.get("id",0) for i in items)+1

def predict_priority_by_deadline(date_str):
    # simple heuristic: closer deadline => higher priority
    if not date_str:
        return "Medium"
    try:
        d = datetime.fromisoformat(date_str)
        now = datetime.utcnow()
        delta = d - now
        if delta <= timedelta(hours=48):
            return "High"
        if delta <= timedelta(days=7):
            return "Medium"
        return "Low"
    except:
        return "Medium"

@app.route("/")
def index():
    tasks = load_json(DATA_FILE, [])
    profile = load_json(PROFILE_FILE, {"name":"Student","course":"", "goals":"", "avatar":""})
    # compute stats
    total = len(tasks)
    completed_tasks = [t for t in tasks if t.get("status")=="Completed"]
    completed = len(completed_tasks)
    pending = total - completed
    predicted_high = sum(1 for t in tasks if predict_priority_by_deadline(t.get("date"))=="High" and t.get("status")!="Completed")
    # priority counts
    counts = {"High":0,"Medium":0,"Low":0}
    for t in tasks:
        p = t.get("priority") or predict_priority_by_deadline(t.get("date"))
        counts[p]=counts.get(p,0)+1
    # top searches
    searches = load_json(SEARCH_FILE, {})
    top_searches = sorted(searches.items(), key=lambda x:-x[1])[:6]
    return render_template("index.html",
                           tasks=tasks,
                           profile=profile,
                           total=total,
                           completed=completed,
                           pending=pending,
                           predicted_high=predicted_high,
                           priority_counts=counts,
                           top_searches=top_searches)

@app.route("/add", methods=["POST"])
def add_task():
    tasks = load_json(DATA_FILE, [])
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    date = request.form.get("date","").strip()
    priority = request.form.get("priority") or predict_priority_by_deadline(date)
    new = {
        "id": next_id(tasks),
        "title": title,
        "description": description,
        "date": date,
        "priority": priority,
        "status": "Pending",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "time_taken_minutes": None
    }
    tasks.insert(0,new)
    save_json(DATA_FILE, tasks)
    return redirect("/")

@app.route("/toggle/<int:task_id>")
def toggle(task_id):
    tasks = load_json(DATA_FILE, [])
    for t in tasks:
        if t.get("id")==task_id:
            if t.get("status")=="Pending":
                t["status"]="Completed"
                t["completed_at"]=datetime.utcnow().isoformat()
                # calculate time taken (if created_at exists)
                try:
                    created = datetime.fromisoformat(t.get("created_at"))
                    taken = datetime.utcnow() - created
                    t["time_taken_minutes"] = int(taken.total_seconds()/60)
                except:
                    t["time_taken_minutes"]=None
            else:
                t["status"]="Pending"
                t["completed_at"]=None
                t["time_taken_minutes"]=None
            break
    save_json(DATA_FILE, tasks)
    return redirect("/")

@app.route("/delete/<int:task_id>")
def delete(task_id):
    tasks = load_json(DATA_FILE, [])
    tasks = [t for t in tasks if t.get("id")!=task_id]
    save_json(DATA_FILE, tasks)
    return redirect("/")

@app.route("/profile", methods=["GET","POST"])
def profile():
    if request.method=="GET":
        profile = load_json(PROFILE_FILE, {"name":"Student","course":"","goals":"","avatar":""})
        return render_template("profile.html", user=profile)
    # POST to update profile
    data = load_json(PROFILE_FILE, {"name":"Student","course":"","goals":"","avatar":""})
    data["name"] = request.form.get("name", data.get("name",""))
    data["course"] = request.form.get("course", data.get("course",""))
    data["goals"] = request.form.get("goals", data.get("goals",""))
    # avatar: for simplicity accept image URL (or base64) in a field
    data["avatar"] = request.form.get("avatar", data.get("avatar",""))
    save_json(PROFILE_FILE, data)
    return redirect("/profile")

@app.route("/search", methods=["POST"])
def search():
    q = request.json.get("q","").strip().lower()
    # store query counts
    searches = load_json(SEARCH_FILE, {})
    if q:
        searches[q]=searches.get(q,0)+1
        save_json(SEARCH_FILE, searches)
    tasks = load_json(DATA_FILE, [])
    results = [t for t in tasks if q in (t.get("title","")+" "+t.get("description","")).lower()]
    return jsonify({"results": results})

@app.route("/top_searches")
def top_searches():
    searches = load_json(SEARCH_FILE, {})
    top = sorted(searches.items(), key=lambda x:-x[1])[:10]
    return jsonify({"top": top})

# AI endpoints
@app.route("/ai_tip")
def ai_tip():
    tips = [
        "Try 25-minute focused sessions with 5-minute breaks (Pomodoro).",
        "Start with the hardest task when you're most alert.",
        "Summarize a topic in your own words to test understanding.",
        "Practice by solving sample problems rather than only reading.",
        "Teach the concept to someone (or pretend to) — it reveals gaps."
    ]
    return jsonify({"tip": random.choice(tips)})

@app.route("/ai_query", methods=["POST"])
def ai_query():
    data = request.get_json() or {}
    question = data.get("question","").strip()
    if not question:
        return jsonify({"answer":"Please ask a question."})
    # If OpenAI key is available, use it; otherwise respond with fallback answer
    if openai.api_key:
        try:
            # use ChatCompletion if available
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content": question}],
                max_tokens=400,
                temperature=0.6
            )
            answer = resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            answer = f"AI service error: {str(e)}"
    else:
        # fallback: simple rule-based friendly response (so demo works offline)
        answer = f"Sorry — no OpenAI key found on the server. Here's a quick guide: try breaking your question into smaller steps. Example: If you asked '{question}', start by defining the key terms, then outline 2–3 main steps to solve it."
    return jsonify({"answer": answer})

@app.route("/static/<path:path>")
def custom_static(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(debug=True)
