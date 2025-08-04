import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from tasks import process_video_task, get_task_result

app = Flask(__name__)
OUTPUT_DIR = "video_sub"

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    url = data.get('url', '').strip()
    if not url or not url.startswith('http'):
        return jsonify({"status": "error", "msg": "无效URL"}), 400
    task_id = str(uuid.uuid4())
    process_video_task.apply_async(args=[url, task_id])
    return jsonify({"task_id": task_id, "status": "queued"})

@app.route('/api/status')
def status():
    task_id = request.args.get('task_id')
    result = get_task_result(task_id)
    return jsonify(result)

@app.route('/api/download/<filename>')
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=8000)
