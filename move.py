import os
import sys
import threading
import webbrowser
import tkinter as tk
import socket
from flask import Flask, render_template, send_from_directory, jsonify, Response

# تحديد مسارات المجلدات
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_PATH = os.path.join(current_dir, 'templates')
BASE_MEDIA_PATH = os.path.join(current_dir, 'media')

app = Flask(__name__, template_folder=TEMPLATE_PATH)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def find_cover(directory, name):
    valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.jfif', '.bmp')
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if f.lower().startswith(name.lower()) and f.lower().endswith(valid_exts):
                return f
    return None

@app.route('/')
def index():
    if not os.path.exists(BASE_MEDIA_PATH):
        return "خطأ: مجلد media غير موجود"
    
    data = {'films': [], 'series': [], 'anime': [], 'music': [], 'all_covers': []}
    video_exts = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')

    for cat in ['films', 'series', 'anime', 'music']:
        cat_path = os.path.join(BASE_MEDIA_PATH, cat)
        if not os.path.exists(cat_path): continue

        for item in os.listdir(cat_path):
            full_path = os.path.join(cat_path, item)
            
            if cat in ['films', 'music'] and item.lower().endswith(video_exts):
                name = os.path.splitext(item)[0]
                cover = find_cover(cat_path, name)
                entry = {
                    'title': name, 
                    'type': cat, 
                    'file': item, 
                    'cover': f'{cat}/{cover}' if cover else 'default.jpg'
                }
                data[cat].append(entry)
                if cat != 'music': data['all_covers'].append(entry)
            
            elif cat in ['series', 'anime'] and os.path.isdir(full_path):
                cover = find_cover(cat_path, item)
                entry = {'title': item, 'type': cat, 'cover': f'{cat}/{cover}' if cover else 'default.jpg'}
                data[cat].append(entry)
                data['all_covers'].append(entry)
                
    return render_template('index.html', media=data)

@app.route('/api/episodes/<category>/<folder>')
def api_episodes(category, folder):
    target = os.path.join(BASE_MEDIA_PATH, category, folder)
    if os.path.exists(os.path.join(target, 's1')): target = os.path.join(target, 's1')
    eps = sorted([f for f in os.listdir(target) if f.lower().endswith(('.mp4', '.mkv', '.avi'))]) if os.path.exists(target) else []
    return jsonify({"episodes": eps})

@app.route('/view/<category>/<folder>')
def view_episodes(category, folder):
    cat_dir = os.path.join(BASE_MEDIA_PATH, category)
    target = os.path.join(cat_dir, folder)
    if os.path.exists(os.path.join(target, 's1')): target = os.path.join(target, 's1')
    cover = find_cover(cat_dir, folder)
    eps = sorted([f for f in os.listdir(target) if f.lower().endswith(('.mp4', '.mkv', '.avi'))]) if os.path.exists(target) else []
    return render_template('index.html', media={'films':[], 'series':[], 'anime':[], 'music':[], 'all_covers':[]}, is_view=True, category=category, folder=folder, episodes=eps, cover=f'{category}/{cover}' if cover else 'default.jpg')

# --- تعديل دالة الاستريم لتجنب بطء الشبكة ---
@app.route('/stream/<path:filename>')
def stream(filename):
    file_path = os.path.join(BASE_MEDIA_PATH, filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404

    def generate():
        with open(file_path, "rb") as f:
            while True:
                # نقرأ 1 ميجا في المرة الواحدة لتخفيف الضغط
                chunk = f.read(1024 * 1024) 
                if not chunk:
                    break
                yield chunk

    return Response(generate(), mimetype="video/mp4")

def run_gui():
    root = tk.Tk()
    root.title("YASSER MOVLEX SERVER")
    root.geometry("400x350")
    root.configure(bg='#141414')
    my_ip = get_ip()

    def start_server():
        # إضافة threaded=True تسمح للسيرفر بالتعامل مع التحميل وتصفح الموقع في آن واحد
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True), daemon=True).start()
        lbl_status.config(text="Server Online ✅", fg="#4CAF50")
        lbl_link.config(text=f"IP: http://{my_ip}:5000")
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:5000")).start()

    tk.Label(root, text="YASSER MOVLEX", fg='#e50914', bg='#141414', font=("Arial", 22, "bold")).pack(pady=25)
    lbl_status = tk.Label(root, text="Server Offline ❌", fg="white", bg="#141414", font=("Arial", 12))
    lbl_status.pack()
    lbl_link = tk.Label(root, text="Ready to start", fg="#aaa", bg="#141414")
    lbl_link.pack(pady=10)
    
    btn_start = tk.Button(root, text="START SERVER", command=start_server, bg='#e50914', fg='white', font=("Arial", 12, "bold"), width=20, height=2)
    btn_start.pack(pady=20)
    
    root.mainloop()

if __name__ == '__main__':
    run_gui()