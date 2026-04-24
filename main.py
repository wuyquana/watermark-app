from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.filechooser import FileChooserListView

import cv2
import numpy as np
import os

# ============ 与电脑端完全一致配置 ============
FIXED_LEN = 48
PWD_IMG = 1
PWD_WM = 1

# ============ 复刻盲水印核心算法 ============
def str_to_bit(s):
    bit_list = []
    for ch in s:
        b = bin(ord(ch))[2:].zfill(8)
        bit_list.extend(int(c) for c in b)
    if len(bit_list) < FIXED_LEN:
        bit_list += [0]*(FIXED_LEN - len(bit_list))
    return bit_list[:FIXED_LEN]

def bit_to_str(bit_list):
    bits = []
    for b in bit_list:
        bits.append(1 if b else 0)
    res = ""
    for i in range(0, len(bits), 8):
        seg = bits[i:i+8]
        if all(x==0 for x in seg):
            break
        res += chr(int("".join(map(str, seg)),2))
    return res.strip()

def add_watermark(img:np.ndarray, wm_bits, seed_img=1, seed_wm=1):
    np.random.seed(seed_img)
    h, w = img.shape[:2]
    length = len(wm_bits)
    idx = np.random.choice(h*w, length, replace=False)
    flat = img.reshape(-1,3)
    for i, pos in enumerate(idx):
        if wm_bits[i]:
            flat[pos,0] = (flat[pos,0] & 0xfe) | 1
        else:
            flat[pos,0] = (flat[pos,0] & 0xfe)
    return flat.reshape(h,w,3)

def extract_watermark(img:np.ndarray, seed_img=1):
    h, w = img.shape[:2]
    np.random.seed(seed_img)
    idx = np.random.choice(h*w, FIXED_LEN, replace=False)
    flat = img.reshape(-1,3)
    bits = []
    for pos in idx:
        bits.append(flat[pos,0] & 1)
    return bits

# ============ 界面配置 ============
Window.clearcolor = get_color_from_hex("#f5f7fa")
Window.size = (360, 640)

# 统一设置中文字体
CHINESE_FONT = "msyh.ttc"

class MainUI(BoxLayout):
    def __init__(self,**kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.selected_path = ""
        self.mode_type = "single"

        # 主内容区：用 ScrollView 包裹，实现上下滑动
        scroll = ScrollView()
        self.main_layout = BoxLayout(orientation="vertical", padding=15, spacing=10, size_hint_y=None)
        self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
        scroll.add_widget(self.main_layout)
        self.add_widget(scroll)

        # 标题
        title = Label(text="盲水印工具 安卓版", font_size=18, bold=True,
                      color=get_color_from_hex("#2c3e50"), font_name=CHINESE_FONT,
                      size_hint_y=None, height=40)
        self.main_layout.add_widget(title)

        # 模式选择
        mode_box = GridLayout(cols=3, size_hint_y=None, height=40)
        self.btn_single = ToggleButton(text="单次加密", group="mode", state="down",
                                       font_name=CHINESE_FONT)
        self.btn_batch = ToggleButton(text="批量加密", group="mode",
                                      font_name=CHINESE_FONT)
        self.btn_decode = ToggleButton(text="解密水印", group="mode",
                                       font_name=CHINESE_FONT)
        self.btn_single.bind(on_press=self.switch_mode)
        self.btn_batch.bind(on_press=self.switch_mode)
        self.btn_decode.bind(on_press=self.switch_mode)
        mode_box.add_widget(self.btn_single)
        mode_box.add_widget(self.btn_batch)
        mode_box.add_widget(self.btn_decode)
        self.main_layout.add_widget(mode_box)

        # 单次配置
        self.single_box = BoxLayout(orientation="vertical",spacing=8, size_hint_y=None, height=60)
        self.wm_input = TextInput(hint_text="输入水印内容(自动2位)", font_size=14,
                                  size_hint_y=None, height=45, font_name=CHINESE_FONT)
        self.single_box.add_widget(self.wm_input)
        self.main_layout.add_widget(self.single_box)

        # 批量配置
        self.batch_box = BoxLayout(orientation="vertical",spacing=8, opacity=0, size_hint_y=None, height=60)
        self.batch_input = TextInput(hint_text="输入结束数字", font_size=14,
                                     size_hint_y=None, height=45, font_name=CHINESE_FONT)
        self.batch_box.add_widget(self.batch_input)
        self.main_layout.add_widget(self.batch_box)

        # 选择图片（去掉图标）
        btn_select = Button(text="选择手机相册图片", background_color=(0.25,0.65,0.95,1),
                            font_size=14, font_name=CHINESE_FONT, size_hint_y=None, height=45)
        btn_select.bind(on_press=self.select_img)
        self.main_layout.add_widget(btn_select)

        # 执行按钮（去掉图标）
        btn_run = Button(text="开始执行", background_color=(0.15,0.8,0.4,1),
                         font_size=15,bold=True, font_name=CHINESE_FONT, size_hint_y=None, height=50)
        btn_run.bind(on_press=self.run_task)
        self.main_layout.add_widget(btn_run)

        # 结果显示
        self.result_label = Label(text="等待操作...", font_size=13,
                                  color=get_color_from_hex("#e53935"), font_name=CHINESE_FONT,
                                  size_hint_y=None, height=30)
        self.main_layout.add_widget(self.result_label)

        # 日志
        log_frame = BoxLayout(size_hint_y=None, height=150)
        self.log_scroll = ScrollView()
        self.log_label = Label(text="运行日志：\n", font_size=11,
                               color=get_color_from_hex("#666666"), markup=True,
                               font_name=CHINESE_FONT, size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.log_scroll.add_widget(self.log_label)
        log_frame.add_widget(self.log_scroll)
        self.main_layout.add_widget(log_frame)

        # 底部署名
        foot = Label(text="程序由 sijin 制作", font_size=10,
                     color=get_color_from_hex("#999999"), size_hint_y=None, height=20,
                     font_name=CHINESE_FONT)
        self.main_layout.add_widget(foot)

    def switch_mode(self, inst):
        if inst == self.btn_single:
            self.mode_type = "single"
            self.single_box.opacity = 1
            self.batch_box.opacity = 0
        elif inst == self.btn_batch:
            self.mode_type = "batch"
            self.single_box.opacity = 0
            self.batch_box.opacity = 1
        else:
            self.mode_type = "decode"
            self.single_box.opacity = 0
            self.batch_box.opacity = 0

    def select_img(self, _):
        fc = FileChooserListView(filters=['*.png','*.jpg','*.jpeg'])
        fc.bind(on_submit=self.choose_img_ok)
        self.add_widget(fc)

    def choose_img_ok(self, fc, path, *args):
        self.selected_path = path[0]
        self.result_label.text = f"已选择图片：{os.path.basename(self.selected_path)}"
        self.remove_widget(fc)

    def log(self,text):
        self.log_label.text += text + "\n"

    def run_task(self,_):
        if not self.selected_path or not os.path.exists(self.selected_path):
            self.result_label.text = "请先选择图片！"
            return
        try:
            img = cv2.imread(self.selected_path)
            save_dir = os.path.dirname(self.selected_path)

            if self.mode_type == "single":
                wm_txt = self.wm_input.text.strip()
                if not wm_txt:
                    self.result_label.text = "请输入水印内容"
                    return
                wm_txt = wm_txt.zfill(2)
                bits = str_to_bit(wm_txt)
                new_img = add_watermark(img, bits, PWD_IMG, PWD_WM)
                out_path = os.path.join(save_dir,f"{wm_txt}_img.jpg")
                cv2.imwrite(out_path, new_img, [cv2.IMWRITE_JPEG_QUALITY,100])
                self.result_label.text = f"✅ 加密成功：{wm_txt}"
                self.log(f"单次加密完成 → {out_path}")

            elif self.mode_type == "batch":
                max_num = int(self.batch_input.text.strip())
                cnt = 0
                for i in range(1, max_num+1):
                    wm_txt = str(i).zfill(2)
                    bits = str_to_bit(wm_txt)
                    new_img = add_watermark(img.copy(), bits, PWD_IMG, PWD_WM)
                    out_path = os.path.join(save_dir,f"{wm_txt}.jpg")
                    cv2.imwrite(out_path, new_img, [cv2.IMWRITE_JPEG_QUALITY,100])
                    cnt +=1
                self.result_label.text = f"✅ 批量完成 共{cnt}张"
                self.log(f"批量加密 1~{max_num} 完成")

            else:
                bits = extract_watermark(img, PWD_IMG)
                res = bit_to_str(bits)
                self.result_label.text = f"🔍 解密结果：{res}"
                self.log(f"解密水印：{res}")

        except Exception as e:
            self.result_label.text = "❌ 执行失败"
            self.log(f"错误：{str(e)}")

class WatermarkApp(App):
    def build(self):
        return MainUI()

if __name__ == "__main__":
    WatermarkApp().run()