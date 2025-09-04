
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os
import json
import google.generativeai as genai

# --- Configure Gemini API ---
genai.configure(api_key="AIzaSyAdE-X2dp3g_YI7tT0BVly8Yrvhds7Wpdo")

# --- Flask setup ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    done = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- Gemini API call ---
def call_gemini(prompt, max_tokens=400):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=max_tokens
            )
        )
        return response.text
    except Exception as e:
        return f"Error calling Gemini API: {e}"

# --- Routes ---
@app.route("/")
def index():
    todos = Todo.query.all()
    return render_template("index.html", todos=todos)

@app.route("/todos", methods=["GET"])
def get_todos():
    todos = Todo.query.filter_by(done=False).all()
    return jsonify([{"id": t.id, "title": t.title, "duration_min": t.duration_min, "done": t.done} for t in todos])

@app.route("/add", methods=["POST"])
def add_todo():
    data = request.json
    new_task = Todo(title=data['title'], duration_min=data['duration_min'])
    db.session.add(new_task)
    db.session.commit()
    return jsonify({"success": True, "task": {"id": new_task.id, "title": new_task.title, "duration_min": new_task.duration_min, "done": new_task.done}})

@app.route("/suggest-order", methods=["POST"])
def suggest_order():
    todos = Todo.query.filter_by(done=False).all()
    prompt = "You are a productivity assistant. Given the tasks with durations in minutes, produce a recommended order to complete them efficiently within one 8-hour day. Return ONLY a JSON array of objects like [{\"id\":1,\"title\":\"Task title\",\"reason\":\"short explanation\"}].\n\nTasks:\n"
    for t in todos:
        prompt += f"- id:{t.id} title:\"{t.title}\" duration:{t.duration_min}min\n"
    ai_text = call_gemini(prompt)
    try:
        suggested = json.loads(ai_text)
        return jsonify({"suggested": suggested})
    except Exception:
        return jsonify({"raw": ai_text})

@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    task = Todo.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    task.done = True
    db.session.commit()
    
    prompt = f"You are an upbeat coach. Someone just completed this task: \"{task.title}\" (duration {task.duration_min} minutes). Give a short 1-2 sentence praise message, friendly tone, include a quick tip to keep momentum. Respond as plain text."
    praise = call_gemini(prompt, max_tokens=80)
    
    return jsonify({"task": {"id": task.id, "title": task.title, "done": task.done}, "praise": praise})

if __name__ == "__main__":
    app.run(debug=True, port=3000)