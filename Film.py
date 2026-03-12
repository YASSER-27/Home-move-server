import os
import sys
import threading
import webbrowser
import socket
import re
import customtkinter as ctk
from PIL import Image, ImageTk
from flask import Flask, render_template, send_from_directory, jsonify, Response, request

# --- إعدادات المسارات ---
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_PATH = os.path.join(current_dir, 'templates')
BASE_MEDIA_PATH = os.path.join(current_dir, 'media')

app = Flask(__name__, template_folder=TEMPLATE_PATH)

# --- دوال السيرفر (منطقك الأصلي) ---
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except: ip = '127.0.0.1'
    finally: s.close()
    return ip

def find_cover(directory, name):
    valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.jfif', '.bmp')
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if f.lower().startswith(name.lower()) and f.lower().endswith(valid_exts):
                return f
    return None

def find_story(directory, name):
    txt_path = os.path.join(directory, f"{name}.txt")
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read().replace("'", "").replace('"', "").replace("\n", " ")
        except: return "تعذر قراءة الوصف."
    return "لا يوجد وصف متاح لهذا العمل."

@app.route('/')
def index():
    if not os.path.exists(BASE_MEDIA_PATH): return "خطأ: مجلد media غير موجود"
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
                story = find_story(cat_path, name) if cat == 'films' else ""
                entry = {'title': name, 'type': cat, 'file': item, 'cover': f'{cat}/{cover}' if cover else 'default.jpg', 'story': story}
                data[cat].append(entry)
                if cat != 'music': data['all_covers'].append(entry)
            elif cat in ['series', 'anime'] and os.path.isdir(full_path):
                cover = find_cover(cat_path, item)
                story = find_story(cat_path, item)
                entry = {'title': item, 'type': cat, 'cover': f'{cat}/{cover}' if cover else 'default.jpg', 'story': story}
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

def generate_video_chunks(path, start, end, chunk_size=1024*1024):
    with open(path, 'rb') as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data: break
            yield data
            remaining -= len(data)

@app.route('/stream/<path:filename>')
def stream(filename):
    file_path = os.path.join(BASE_MEDIA_PATH, filename)
    if not os.path.exists(file_path): return "File not found", 404
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))
    byte1, byte2 = 0, None
    m = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if m:
        byte1 = int(m.group(1))
        if m.group(2): byte2 = int(m.group(2))
    if byte2 is None: byte2 = file_size - 1
    length = byte2 - byte1 + 1
    resp = Response(generate_video_chunks(file_path, byte1, byte2), status=206, mimetype='video/mp4', content_type='video/mp4')
    resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(length))
    return resp

# --- واجهة Raycast Style المطورة ---
class MovlexGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # إعدادات النافذة (بدون حواف ويندوز التقليدية)
        self.title("Raycast")
        self.geometry("420x350")
        self.configure(fg_color='#0c0c0c') # أسود صافي
        self.overrideredirect(True) # حذف شريط العنوان (فخامة Raycast)
        
        # توسيط النافذة
        self.center_window()

        # الإطار الرئيسي بحواف نحيفة
        self.main_frame = ctk.CTkFrame(self, fg_color="#0c0c0c", border_color="#222222", border_width=1, corner_radius=20)
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # زر الإغلاق في الزاوية
        self.close_btn = ctk.CTkLabel(self.main_frame, text="×", text_color="#555", font=("Arial", 20), cursor="hand2")
        self.close_btn.place(x=380, y=10)
        self.close_btn.bind("<Button-1>", lambda e: self.destroy())

        # المحتوى
        self.lbl_main = ctk.CTkLabel(self.main_frame, text="YASSER MOVLEX", text_color='#ffffff', font=("Segoe UI", 26, "bold"))
        self.lbl_main.pack(pady=(60, 5))

        self.lbl_status = ctk.CTkLabel(self.main_frame, text="● SERVER ONLINE", text_color="#32d74b", font=("Segoe UI", 11, "bold"))
        self.lbl_status.pack()

        self.lbl_link = ctk.CTkLabel(self.main_frame, text="Connecting...", text_color="#444", font=("Consolas", 11))
        self.lbl_link.pack(pady=20)

        # زر Raycast (أبيض مع نص أسود)
        self.btn_open = ctk.CTkButton(self.main_frame, text="Open Dashboard", command=self.open_browser, 
                                     fg_color="white", text_color="black", font=("Segoe UI", 13, "bold"),
                                     hover_color="#eee", height=40, width=220, corner_radius=10)
        self.btn_open.pack(pady=30)

        # ميزة سحب النافذة
        self.main_frame.bind("<ButtonPress-1>", self.start_move)
        self.main_frame.bind("<B1-Motion>", self.do_move)

        self.start_automatic_server()

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (420 // 2)
        y = (screen_height // 2) - (350 // 2)
        self.geometry(f"+{x}+{y}")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        self.geometry(f"+{self.winfo_x() + deltax}+{self.winfo_y() + deltay}")

    def start_automatic_server(self):
        my_ip = get_ip()
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, threaded=True), daemon=True).start()
        self.lbl_link.configure(text=f"http://{my_ip}:5000")
        self.after(1200, self.open_browser)

    def open_browser(self):
        webbrowser.open(f"http://127.0.0.1:5000")

if __name__ == '__main__':
    gui = MovlexGUI()
    gui.mainloop()