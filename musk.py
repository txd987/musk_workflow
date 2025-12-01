import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
import json
import webbrowser
import os
import platform
import pyperclip

class ButtonEditor(tk.Toplevel):
    """ 编辑器弹窗 """
    def __init__(self, parent, current_data, on_save):
        super().__init__(parent)
        self.title("配置按钮功能")
        self.geometry("450x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        self.current_data = current_data or {}
        
        # 将窗口居中显示
        self.update_idletasks()
        window_width = 450
        window_height = 450
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="按钮标题:").pack(pady=(20, 5), anchor="w", padx=20)
        self.title_entry = tk.Entry(self, width=50)
        self.title_entry.pack(padx=20)
        self.title_entry.insert(0, self.current_data.get("title", ""))

        tk.Label(self, text="功能类型:").pack(pady=(15, 5), anchor="w", padx=20)
        self.type_var = tk.StringVar(value=self.current_data.get("type", "url"))
        self.type_var.trace('w', self.on_type_change)
        type_frame = tk.Frame(self)
        type_frame.pack(anchor="w", padx=20)
        tk.Radiobutton(type_frame, text="网页链接", variable=self.type_var, value="url").pack(side="left", padx=(0, 10))
        tk.Radiobutton(type_frame, text="本地文件夹", variable=self.type_var, value="folder").pack(side="left", padx=(0, 10))
        tk.Radiobutton(type_frame, text="本地文件", variable=self.type_var, value="file").pack(side="left", padx=(0, 10))
        tk.Radiobutton(type_frame, text="复制文本", variable=self.type_var, value="clipboard").pack(side="left")

        tk.Label(self, text="路径 / 网址 / 文本:").pack(pady=(15, 5), anchor="w", padx=20)
        input_frame = tk.Frame(self)
        input_frame.pack(padx=20, fill="both", expand=True)
        
        # 单行输入框（用于URL/文件/文件夹）
        self.value_entry = tk.Entry(input_frame)
        self.value_entry.pack(side="left", fill="x", expand=True)
        self.value_entry.insert(0, self.current_data.get("value", ""))
        self.browse_btn = tk.Button(input_frame, text="浏览...", command=self.browse_path)
        self.browse_btn.pack(side="right", padx=(5, 0))
        
        # 多行文本框（用于clipboard）
        self.value_text = scrolledtext.ScrolledText(input_frame, width=50, height=8, wrap=tk.WORD)
        self.value_text.insert("1.0", self.current_data.get("value", ""))
        
        self.on_type_change()  # 初始化显示正确的输入控件

        btn_frame = tk.Frame(self)
        btn_frame.pack(side="bottom", pady=20, fill="x")
        tk.Button(btn_frame, text="清空此位", bg="#ffcdd2", command=self.clear_data).pack(side="left", padx=20)
        tk.Button(btn_frame, text="保存配置", bg="#c8e6c9", width=15, command=self.save_data).pack(side="right", padx=20)

    def on_type_change(self, *args):
        """根据类型切换输入控件"""
        current_type = self.type_var.get()
        if current_type == "clipboard":
            self.value_entry.pack_forget()
            self.browse_btn.pack_forget()
            self.value_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        else:
            self.value_text.pack_forget()
            self.value_entry.pack(side="left", fill="x", expand=True)
            self.browse_btn.pack(side="right", padx=(5, 0))
    
    def browse_path(self):
        current_type = self.type_var.get()
        path = ""
        if current_type == "folder":
            path = filedialog.askdirectory()
        elif current_type == "file":
            path = filedialog.askopenfilename()
        if path:
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, path)

    def save_data(self):
        title = self.title_entry.get().strip()
        current_type = self.type_var.get()
        
        # 根据类型获取值
        if current_type == "clipboard":
            value = self.value_text.get("1.0", tk.END).strip()
        else:
            value = self.value_entry.get().strip()
        
        if not title or not value:
            messagebox.showwarning("提示", "标题和内容不能为空")
            return
        self.on_save({"title": title, "type": current_type, "value": value})
        self.destroy()

    def clear_data(self):
        self.on_save(None)
        self.destroy()


class MuskWorkflowApp:
    def __init__(self, root):
        self.root = root
        self.root.title("马斯克工作流 (支持拖拽排序)")
        self.root.geometry("900x650")
        
        self.config_file = os.path.join(os.path.expanduser("~"), ".musk_workflow_config.json")
        self.app_data = self.load_config()

        # 用于存储拖拽状态
        self.drag_data = {
            "start_x": 0,
            "start_y": 0,
            "source_idx": None,
            "tab_idx": None,
            "is_dragging": False
        }
        
        # 存储当前页面所有按钮组件的引用，方便查找
        self.current_buttons_map = {} 

        self.create_menu()
        
        hint_frame = tk.Frame(self.root, bg="#fff3cd", pady=5)
        hint_frame.pack(fill="x")
        tk.Label(hint_frame, text="💡 提示：按住左键拖拽可交换位置 | 双击标签重命名 | 右键编辑", bg="#fff3cd").pack(side="left", padx=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', pady=5)
        self.notebook.bind("<Double-1>", self.on_tab_double_click)

        self.refresh_ui()
        
        # 绑定快捷键
        self.root.bind("<Control-s>", lambda e: self.auto_save())
        self.root.bind("<Control-S>", lambda e: self.auto_save())
        
        # 窗口关闭时自动保存
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def generate_default_config(self):
        default_names = ["日常工作", "星球", "公众号", "审稿与回复", "blogger", "个人健康", "孩子教育", "小红书", "财务管理", "系统设置"]
        data = []
        for name in default_names:
            data.append({"name": name, "buttons": [None] * 10})
        return data
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self.generate_default_config()
    
    def auto_save(self):
        """自动保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"自动保存失败: {e}")
    
    def on_closing(self):
        """窗口关闭时保存配置"""
        self.auto_save()
        self.root.destroy()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存配置 (Ctrl+S)", command=self.auto_save)
        file_menu.add_separator()
        file_menu.add_command(label="导入配置", command=self.import_json)
        file_menu.add_command(label="导出配置", command=self.export_json)
        menubar.add_cascade(label="文件", menu=file_menu)
        self.root.config(menu=menubar)

    def refresh_ui(self):
        current_tab_index = 0
        try: current_tab_index = self.notebook.index(self.notebook.select())
        except: pass

        for tab in self.notebook.tabs(): self.notebook.forget(tab)
        self.current_buttons_map = {} # 清空引用

        for tab_idx, tab_info in enumerate(self.app_data):
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=f" {tab_info['name']} ")
            
            grid_frame = tk.Frame(tab_frame)
            grid_frame.pack(pady=20, padx=20, expand=True)

            for i in range(10):
                row = i // 2
                col = i % 2
                btn_info = tab_info["buttons"][i] if i < len(tab_info["buttons"]) else None
                self.create_button(grid_frame, tab_idx, i, btn_info, row, col)
        
        if current_tab_index < len(self.notebook.tabs()):
            self.notebook.select(current_tab_index)

    def create_button(self, parent, tab_index, btn_index, btn_info, row, col):
        """创建支持拖拽的按钮"""
        text = "[ 空位 ]"
        bg_color = "#f8f9fa"
        
        if btn_info and btn_info.get("title"):
            t = btn_info.get("title")
            b_type = btn_info.get("type", "")
            if b_type == "url": bg_color, icon = "#e3f2fd", "🌐 "
            elif b_type == "folder": bg_color, icon = "#f3e5f5", "📂 "
            elif b_type == "file": bg_color, icon = "#e8f5e9", "📄 "
            elif b_type == "clipboard": bg_color, icon = "#fff9c4", "📋 "
            else: bg_color, icon = "#eeeeee", "❓ "
            text = f"{icon}{t}"
        
        btn = tk.Button(parent, text=text, bg=bg_color, width=28, height=3, font=("微软雅黑", 10), wraplength=200)
        btn.grid(row=row, column=col, padx=10, pady=10)
        
        # 添加tooltip
        if btn_info and btn_info.get("value"):
            self.create_tooltip(btn, btn_info.get("value"))

        # 存储引用，用于拖拽释放时的检测
        # key 是组件的内存ID (widget._w)，value 是按钮在当前页面的索引
        self.current_buttons_map[str(btn)] = btn_index
        
        # --- 核心：绑定拖拽和点击事件 ---
        # 1. 鼠标按下：记录起点
        btn.bind("<ButtonPress-1>", lambda e, ti=tab_index, bi=btn_index: self.on_press(e, ti, bi))
        # 2. 鼠标移动：检测是否在拖拽
        btn.bind("<B1-Motion>", self.on_motion)
        # 3. 鼠标释放：执行点击 或 完成拖拽
        btn.bind("<ButtonRelease-1>", lambda e, bi=btn_index, info=btn_info: self.on_release(e, bi, info))

        # 4. 右键编辑 (Mac兼容)
        btn.bind("<Button-3>", lambda e: self.open_editor(tab_index, btn_index))
        if platform.system() == "Darwin":
             btn.bind("<Button-2>", lambda e: self.open_editor(tab_index, btn_index))
             btn.bind("<Control-Button-1>", lambda e: self.open_editor(tab_index, btn_index))
    
    def create_tooltip(self, widget, text):
        """创建tooltip显示完整信息"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("微软雅黑", 9), wraplength=300)
            label.pack()
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    # --- 拖拽逻辑开始 ---
    
    def on_press(self, event, tab_idx, btn_idx):
        self.drag_data["start_x"] = event.x
        self.drag_data["start_y"] = event.y
        self.drag_data["source_idx"] = btn_idx
        self.drag_data["tab_idx"] = tab_idx
        self.drag_data["is_dragging"] = False

    def on_motion(self, event):
        # 只有移动超过一定距离才算是拖拽，防止点击抖动
        if not self.drag_data["is_dragging"]:
            dx = abs(event.x - self.drag_data["start_x"])
            dy = abs(event.y - self.drag_data["start_y"])
            if dx > 5 or dy > 5:
                self.drag_data["is_dragging"] = True
                self.root.config(cursor="fleur") # 改变鼠标形状为移动图标

    def on_release(self, event, btn_index, btn_info):
        # 恢复鼠标形状
        self.root.config(cursor="")
        
        if self.drag_data["is_dragging"]:
            # === 这里是拖拽结束逻辑 ===
            # 获取鼠标在屏幕上的绝对位置
            x, y = event.x_root, event.y_root
            # 找到该位置下的组件
            target_widget = self.root.winfo_containing(x, y)
            
            # 检查这个组件是否是我们已知的按钮之一
            target_index = None
            if target_widget:
                # winfo_containing 可能返回按钮内部的 Label 或 Canvas (虽然 Button 主要是整体)
                # 直接通过 widget 对象转字符串去 map 里查
                w_str = str(target_widget)
                if w_str in self.current_buttons_map:
                    target_index = self.current_buttons_map[w_str]
            
            if target_index is not None and target_index != self.drag_data["source_idx"]:
                # 执行交换
                self.swap_buttons(self.drag_data["tab_idx"], self.drag_data["source_idx"], target_index)
            
            # 重置状态
            self.drag_data["is_dragging"] = False
        
        else:
            # === 这里是普通点击逻辑 ===
            self.execute_action(btn_info)

    def swap_buttons(self, tab_idx, source_idx, target_idx):
        """交换两个按钮的数据并刷新"""
        buttons = self.app_data[tab_idx]["buttons"]
        # Python 交换变量的语法糖
        buttons[source_idx], buttons[target_idx] = buttons[target_idx], buttons[source_idx]
        # 刷新界面
        self.refresh_ui()

    # --- 拖拽逻辑结束 ---

    def execute_action(self, info):
        if not info: return
        action_type = info.get("type")
        value = info.get("value")
        try:
            if action_type == "url":
                if not value.startswith(("http://", "https://")): value = "http://" + value
                webbrowser.open(value)
            elif action_type in ["folder", "file"]:
                if os.path.exists(value):
                    if platform.system() == "Windows": os.startfile(value)
                    elif platform.system() == "Darwin": os.system(f"open '{value}'")
                    else: os.system(f"xdg-open '{value}'")
                else:
                    messagebox.showerror("错误", f"路径不存在:\n{value}")
            elif action_type == "clipboard":
                try:
                    pyperclip.copy(value)
                    # 使用非阻塞的状态提示
                    self.show_status_message("✓ 已复制到剪贴板")
                except Exception as e:
                    messagebox.showerror("错误", f"复制失败: {str(e)}")
        except Exception as e:
            messagebox.showerror("执行错误", str(e))

    def on_tab_double_click(self, event):
        try:
            clicked_tab_index = self.notebook.index(f"@{event.x},{event.y}")
            current_data = self.app_data[clicked_tab_index]
            new_name = simpledialog.askstring("重命名", "输入新名称:", initialvalue=current_data["name"])
            if new_name and new_name.strip():
                self.app_data[clicked_tab_index]["name"] = new_name.strip()
                self.notebook.tab(clicked_tab_index, text=f" {new_name.strip()} ")
        except: pass

    def show_status_message(self, message, duration=1500):
        """显示状态消息（自动消失）"""
        status_win = tk.Toplevel(self.root)
        status_win.wm_overrideredirect(True)
        status_win.attributes('-topmost', True)
        
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 200) // 2
        y = screen_height - 150
        status_win.geometry(f"200x50+{x}+{y}")
        
        label = tk.Label(status_win, text=message, bg="#4CAF50", fg="white", font=("微软雅黑", 10, "bold"), pady=10)
        label.pack(fill="both", expand=True)
        
        # 自动关闭
        self.root.after(duration, status_win.destroy)
    
    def open_editor(self, tab_idx, btn_idx):
        current = self.app_data[tab_idx]["buttons"][btn_idx]
        def save(new_data):
            self.app_data[tab_idx]["buttons"][btn_idx] = new_data
            self.refresh_ui()
            self.auto_save()  # 编辑后自动保存
        ButtonEditor(self.root, current, save)

    def import_json(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    d = json.load(file)
                    if isinstance(d, list): 
                        self.app_data = d
                        self.refresh_ui()
                        self.auto_save()
                        messagebox.showinfo("成功", "配置已导入")
            except Exception as e: 
                messagebox.showerror("导入失败", str(e))

    def export_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if f:
            try:
                with open(f, 'w', encoding='utf-8') as file:
                    json.dump(self.app_data, file, indent=4, ensure_ascii=False)
                messagebox.showinfo("成功", "配置已导出")
            except Exception as e:
                messagebox.showerror("导出失败", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = MuskWorkflowApp(root)
    root.mainloop()