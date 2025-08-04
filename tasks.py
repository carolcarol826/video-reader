import os
import json
from celery import Celery
from process_single_url import process_single_url

app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
RESULT_FILE = "task_results.json"
OUTPUT_DIR = "video_sub"

def save_result(task_id, status, txt_file=None, wav_file=None, msg=""):
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    else:
        results = {}
    results[task_id] = {"status": status, "txt_url": txt_file, "wav_url": wav_file, "msg": msg}
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

def get_task_result(task_id):
    if not os.path.exists(RESULT_FILE):
        return {"status": "not_found"}
    with open(RESULT_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)
    return results.get(task_id, {"status": "not_found"})

@app.task
def process_video_task(url, task_id):
    try:
        txt_file, wav_file = process_single_url(url, task_id, OUTPUT_DIR)
        save_result(task_id, "finished", f"/api/download/{os.path.basename(txt_file)}", f"/api/download/{os.path.basename(wav_file)}")
    except Exception as e:
        save_result(task_id, "failed", None, None, msg=str(e))
