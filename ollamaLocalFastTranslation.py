import time
import requests
import pyperclip
import threading
import tkinter as tk
from pynput import keyboard

# --- 配置项 ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"
DEFAULT_LANG = "Japanese"
TOGGLE_LANG = "English"
HOTKEY_TRANSLATE = keyboard.Key.f5
HOTKEY_SWITCH = keyboard.Key.f4
HUD_SIZE = "180x30"
HUD_COLOR_BG = "#2C3E50"
HUD_COLOR_FG = "#ECF0F1"

# --- 全局变量 ---
target_lang = DEFAULT_LANG
root = None
label = None
ctrl = keyboard.Controller()

def log(msg):
    print(f"[*] {time.strftime('%H:%M:%S')} - {msg}")

def translate_api(text):
    """调用 Ollama API"""
    try:
        log(f"请求翻译 ({target_lang}): {text[:20]}...")
        payload = {
            "model": MODEL_NAME,
            "prompt": f"You are a professional translator. Translate this Chinese text to {target_lang} directly without any explanation or thoughts: {text}",
            "stream": False
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        
        # 处理 DeepSeek 可能包含的 <think> 标签
        raw_res = resp.json().get("response", "").strip()
        final_text = raw_res.split("</think>")[-1].strip() if "</think>" in raw_res else raw_res
        
        log("API 响应成功")
        return final_text
    except Exception as e:
        log(f"API 异常: {e}")
        return None

def update_hud(text, visible=True):
    """线程安全地更新界面"""
    if root and label:
        root.after(0, lambda: label.config(text=text))
        root.after(0, lambda: root.attributes("-alpha", 1.0 if visible else 0.0))

def run_translation():
    """核心翻译流程"""
    try:
        update_hud(f"正在翻译 {target_lang}...")
        
        # 1. 自动剪切
        with ctrl.pressed(keyboard.Key.ctrl):
            ctrl.press('x')
            ctrl.release('x')
        time.sleep(0.3) 

        # 2. 获取并验证文本
        source = pyperclip.paste()
        if not source.strip():
            log("警告: 剪切板内容为空")
            update_hud("", False)
            return

        # 3. 执行翻译
        result = translate_api(source)
        
        if result:
            pyperclip.copy(result)
            with ctrl.pressed(keyboard.Key.ctrl):
                ctrl.press('v')
                ctrl.release('v')
            log(f"翻译成功: {len(source)} -> {len(result)} 字符")
        else:
            log("错误: 翻译返回结果为空")
            
    except Exception as e:
        log(f"运行流程故障: {e}")
    finally:
        time.sleep(0.5)
        update_hud("", False)

def create_hud():
    global root, label
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True, "-alpha", 0.0)
    
    # 屏幕右下角定位
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{HUD_SIZE}+{sw-200}+{sh-80}")
    
    label = tk.Label(root, text="", bg=HUD_COLOR_BG, fg=HUD_COLOR_FG, 
                     font=("Microsoft YaHei", 9, "bold"), padx=10)
    label.pack(fill=tk.BOTH, expand=True)
    root.mainloop()

def on_press(key):
    global target_lang
    try:
        if key == HOTKEY_TRANSLATE:
            threading.Thread(target=run_translation, daemon=True).start()
        elif key == HOTKEY_SWITCH:
            target_lang = TOGGLE_LANG if target_lang == DEFAULT_LANG else DEFAULT_LANG
            log(f"切换语言 -> {target_lang}")
            update_hud(f"模式: {target_lang}")
            threading.Timer(1.5, lambda: update_hud("", False)).start()
    except Exception as e:
        log(f"按键处理异常: {e}")

if __name__ == "__main__":
    log(f"程序启动 | 模型: {MODEL_NAME} | 目标: {target_lang}")
    log(f"快捷键: {HOTKEY_TRANSLATE} 翻译, {HOTKEY_SWITCH} 切换")
    
    # 启动 UI 线程
    threading.Thread(target=create_hud, daemon=True).start()
    
    with keyboard.Listener(on_press=on_press, on_release=lambda k: k != keyboard.Key.insert) as l:
        l.join()
