import sys
import cv2
import base64
import requests
import numpy as np

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

# 百度AI API配置
API_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v1/body_attr"
ACCESS_TOKEN = '24.8f712ae7f0b4107165b27ac2fd9b78a3.2592000.1722778058.282335-90987764'

# 汉英翻译
translation_dict = {
    '红': 'Red',
    '橙': 'Orange',
    '黄': 'Yellow',
    '绿': 'Green',
    '蓝': 'Blue',
    '紫': 'Purple',
    '粉': 'Pink',
    '黑': 'Black',
    '白': 'White',
    '灰': 'Grey',
    '棕': 'Brown',
    '无': 'No',
    '无帽': 'No hat',
    '普通帽': 'Regular hat',
    '安全帽': 'Safety helmet'
}


# 翻译函数
def translate_to_english(chinese_text):
    return translation_dict.get(chinese_text, chinese_text)

# UI生成的代码，此处为伪代码，实际需要将转换后的UI代码复制到这里
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        # 设置窗口标题和大小
        MainWindow.setWindowTitle("人体检测系统")
        MainWindow.setGeometry(100, 100, 800, 600)

        # 设置主窗口的中心部件和布局
        self.centralwidget = QWidget(MainWindow)
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.frame = QFrame(self.centralwidget)
        self.verticalLayout = QVBoxLayout(self.frame)

        # 添加用于显示视频的Label
        self.videoLabel = QLabel(self.frame)
        self.verticalLayout.addWidget(self.videoLabel)

        # 添加进入系统的按钮
        self.enterButton = QPushButton("进入系统", self.frame)
        self.enterButton.clicked.connect(MainWindow.enterSystem)
        self.verticalLayout.addWidget(self.enterButton)

        # 设置布局
        self.horizontalLayout.addWidget(self.frame)
        MainWindow.setCentralWidget(self.centralwidget)


# 主窗口类
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 初始化视频处理相关变量
        self.video_path = 'data/vd1.mp4'  # 视频文件路径，根据实际情况修改
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateFrame)

        # 其他变量
        self.frame_count = 0
        self.num_people = 0


    # 进入系统按钮点击事件处理函数
    def enterSystem(self):
        print("进入系统按钮已点击")
        self.startVideoCapture()

    # 开始视频捕获和处理
    def startVideoCapture(self):
        print(f"尝试打开视频文件: {self.video_path}")
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print("Error: Could not open video.")
            return

        print("视频文件已成功打开，启动定时器")
        self.timer.start(30)  # 每30毫秒更新一次视频帧

    # 调用百度API进行人体检测和属性识别
    def detectPeople(self, frame):
        print("调用百度API进行人体检测和属性识别")
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')

        try:
            response = self.call_baidu_api(img_base64)
            if response:
                print("API调用结果: ", response)
                self.draw_detection(frame, response)
                return frame, response.get('person_num', 0)
            else:
                print("API调用失败: 未收到有效响应")
                return frame, 0
        except Exception as e:
            print("API调用失败: ", e)
            return frame, 0

    # 调用百度API发送请求
    def call_baidu_api(self, img_base64):
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        params = {"image": img_base64, "access_token": ACCESS_TOKEN}

        response = requests.post(API_URL, data=params, headers=headers, verify=True)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API请求失败: {response.status_code}, {response.reason}")
            return None

    # 更新视频帧显示
    def updateFrame(self):
        print("更新视频帧显示")
        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1
            frame_with_detection, num_people = self.detectPeople(frame)
            self.num_people = num_people
            self.displayFrame(frame_with_detection)
            self.displayNumPeople()
        else:
            print("No frame captured, exiting...")
            self.timer.stop()
            self.cap.release()

    # 在界面上显示视频帧
    def displayFrame(self, frame):
        print("显示视频帧")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(800, 600, Qt.KeepAspectRatio)
        self.videoLabel.setPixmap(QPixmap.fromImage(p))

    # 在界面上显示人数统计
    def displayNumPeople(self):
        text = f"当前人数: {self.num_people}"
        self.enterButton.setText(text)

    # 绘制检测框和属性信息
    def draw_detection(self, frame, response):
        person_infos = response.get('person_info', [])
        for person in person_infos:
            location = person['location']
            x, y, w, h = int(location['left']), int(location['top']), \
                int(location['width']), int(location['height'])

            # 绘制人物检测框
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # 检查人物上衣颜色
            upper_color = person.get('attributes', {}).get('upper_color', {}).get('name', 'Unknown')
            translated_upper_color = translate_to_english(upper_color)  # 翻译上衣颜色为英文

            # 检查人物是否戴帽子
            headwear = person.get('attributes', {}).get('headwear', {}).get('name', 'No')
            translated_headwear = translate_to_english(headwear)  # 翻译戴帽子信息为英文

            # 在人物框的头顶显示属性信息
            text_x = x
            text_y = y - 10  # 向上微调，显示在人物框的上方
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 1
            font_color = (0, 0, 255)  # 红色

            cv2.putText(frame,  translated_upper_color, (text_x, text_y), font, font_scale, font_color,
                        font_thickness,
                        lineType=cv2.LINE_AA)
            cv2.putText(frame,translated_headwear, (text_x, text_y + 20), font, font_scale, font_color,
                        font_thickness, lineType=cv2.LINE_AA)

            # 在控制台输出属性信息以便验证
            print(f"Position ({x}, {y}): Upper color - {translated_upper_color}, Wearing hat - {translated_headwear}")

        # 更新UI中显示的帧
        self.displayFrame(frame)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
