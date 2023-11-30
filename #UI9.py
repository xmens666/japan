#UI9
import sys
import os
import time
import json
import threading
import subprocess

from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QWidget, QCheckBox, QLabel, 
                             QDateTimeEdit, QCalendarWidget, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QTextCursor, QColor, QMovie
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QDateTime, QTimer, QEvent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from order_processing import process_orders  # 确保order_processing.py在同一文件夹内


            
# 用于重定向输出的类
class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))
    def flush(self):
        pass

# 主窗口类定义
class OrderManagementApp(QMainWindow):
    # 定义一个自定义信号
    update_order_data_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("订单管理界面")
        # 设置窗口始终在最前端
        self.repeat_run_count = 0 
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.init_ui()
        self.lock = threading.Lock()
        # 将自定义信号连接到更新 UI 的槽函数
        self.update_order_data_signal.connect(self.update_order_data_on_ui)

    def init_ui(self):
        # 设置窗口大小和位置
        screen_geometry = QApplication.primaryScreen().geometry()
        self.resize(screen_geometry.width() * 2 // 3, screen_geometry.height() * 2 // 3)
        self.move(screen_geometry.center() - self.rect().center())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        
        # 左侧布局
        left_layout = QVBoxLayout()

        # 将标题定义为类的属性
        self.new_orders_label = QLabel("新订单")
        self.new_orders_text = QTextEdit()
        left_layout.addWidget(self.new_orders_label)
        left_layout.addWidget(self.new_orders_text)
        
        self.received_orders_label = QLabel("已接订单")
        self.received_orders_text = QTextEdit()
        left_layout.addWidget(self.received_orders_label)
        left_layout.addWidget(self.received_orders_text)

        self.confirmed_orders_label = QLabel("可接订单")
        self.confirmed_orders_text = QTextEdit()
        left_layout.addWidget(self.confirmed_orders_label)
        left_layout.addWidget(self.confirmed_orders_text)

        # 右侧布局
        right_layout = QVBoxLayout()
        monitor_label = QLabel("运行监视器")
        right_layout.addWidget(monitor_label)
        self.details_text = QTextEdit()

        self.details_text.setStyleSheet("""
            color: Lime; /* 设置默认文本颜色为绿色 */
            font-family: 'Menlo', sans-serif;
        """)

        right_layout.addWidget(self.details_text)

        # 在右侧布局中添加一个新窗口
        new_window_label = QLabel("当前接单设置")
        new_window_text = QTextEdit()
        new_window_text.setHtml("""
            <p><span style='color: red;'>接单时间:</span><br>平日:6:00-8:00;17:00-19:00/周末:6:00-20:00</p>
            <p><span style='color: red;'>特殊设置:</span><br>送机单时间范围:6:30-12:00;18:00-21:30</p>
            <p><span style='color: red;'>特殊设置:</span><br>不接成田单</p>
            <p><span style='color: red;'>特殊设置:</span><br>不接5人单和婴儿座椅需求单</p>
        """)
        new_window_text.setStyleSheet("""
            color: Teal; /* 设置默认文本颜色为绿色 */
            font-family: 'Helvetica Neue', sans-serif;
        """)

        right_layout.addWidget(new_window_label)
        right_layout.addWidget(new_window_text)

        # 添加时钟显示
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)  # 更新频率为1秒

        self.clock_label = QLabel("0000-00-00 00:00:00", self)  # 创建一个标签用于显示时间
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置文字居中

        self.clock_label.setStyleSheet("""
            QLabel {
                color: Lime;
                font-size: 24px;
                font-weight: bold;
            }
        """)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(5)  # 阴影模糊半径
        shadow_effect.setColor(QColor('black'))  # 阴影颜色
        shadow_effect.setOffset(3)  # 阴影偏移

        self.clock_label.setGraphicsEffect(shadow_effect)

        right_layout.addWidget(self.clock_label)  # 将时钟标签添加到布局中

        # 添加按钮和复选框
        start_button = QPushButton("打开目标网站")
        analyze_button = QPushButton("开始自动分析可接订单")
        self.auto_accept_checkbox = QCheckBox("选择后自动接单")
        self.auto_accept_checkbox.setStyleSheet("color: red;")
        self.repeat_checkbox = QCheckBox("重复运行")

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.auto_accept_checkbox)
        checkbox_layout.addWidget(self.repeat_checkbox)
        right_layout.addWidget(start_button)
        right_layout.addWidget(analyze_button)
        right_layout.addLayout(checkbox_layout)

        # 将左右布局添加到主布局中
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

        # 连接按钮事件
        start_button.clicked.connect(self.start_program)
        analyze_button.clicked.connect(self.start_analysis)

        # 用于重定向输出的设置
        self.stream = Stream()
        self.stream.newText.connect(self.on_new_text)
        sys.stdout = self.stream

    def setup_order_section(self, layout, title, text_edit, count_label):
        """设置订单部分的布局"""
        title_label = QLabel(title)
        hbox = QHBoxLayout()
        hbox.addWidget(text_edit, 4)  # 文本框占据更大空间
        hbox.addWidget(count_label, 1)  # 数量标签占据更小空间
        layout.addWidget(title_label)
        layout.addLayout(hbox)

    def on_new_text(self, text):
        self.details_text.moveCursor(QTextCursor.MoveOperation.End)
        self.details_text.insertPlainText(text)
        QApplication.processEvents()

    def start_program(self):
        # 运行Selenium脚本的线程
        threading.Thread(target=self.run_selenium_script, daemon=True).start()

    def run_selenium_script(self):
        # 启动带有远程调试端口的Chrome实例
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        debugging_port = "--remote-debugging-port=9222"
        user_data_dir = "--user-data-dir=" + os.path.expanduser("~") + "/ChromeProfile"
        subprocess.Popen([chrome_path, debugging_port, user_data_dir])
        time.sleep(2)  # 等待浏览器启动

        # 指定远程调试端口
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        # 设置ChromeDriver路径并初始化Service对象
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # 连接到已经打开的Chrome实例
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 在新的标签页中打开网页
        driver.execute_script("window.open('https://elifelimo.com/fleet/', '_blank');")

        # 切换到新打开的标签页
        driver.switch_to.window(driver.window_handles[-1])
        print("打开网页")

        # 循环检查页面是否加载成功或出现 "sorry" 文本
        while True:
            try:
                # 检查是否存在包含 "sorry" 的元素
                message_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'sorry')]")
                if message_elements:
                    print("检测到 'sorry' 文本，正在刷新页面...")
                    driver.refresh()
                    time.sleep(5)
                    continue

                # 等待特定的<div>元素出现
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@name='title' and contains(text(), 'This list is visible to many fleets')]"))
                )
                print("页面加载成功")
                break
            except TimeoutException:
                print("等待超时 - 网页未能在指定时间内加载完毕，请刷新")




    def start_analysis(self):
        print("订单分析开始...")
        threading.Thread(target=self.process_orders_thread, daemon=True).start()

    def process_orders_thread(self):
        with self.lock:
            process_orders()
        print("订单分析结束,如果您想开始自动化接单程序请勾选✅自动接新订单选项>")
        self.update_order_data_signal.emit()

        # 确保UI更新已完成
        QApplication.processEvents()

        # 检查复选框是否被选中，然后在新的线程中运行 run_auto_accept
        if self.auto_accept_checkbox.isChecked():
            print("自动接单选项已选中，启动自动接单程序。")
            threading.Thread(target=self.call_external_script, daemon=True).start()



    def call_external_script(self):
        from Auto_take_orders import run_auto_accept
        run_auto_accept()

        # 检查 "重复运行" 复选框是否被选中
        if self.repeat_checkbox.isChecked():
            time.sleep(120)
            self.repeat_run_count += 1  # 增加重复运行次数
            self.update_repeat_run_count_on_ui()  # 更新 UI 上的显示
            self.simulate_analysis_click()


    def simulate_analysis_click(self):
        # 模拟点击分析按钮的逻辑
        print("重新开始自动分析可接订单...")
        self.start_analysis()


    def format_text_with_color(self, text, color):
        # 添加 line-height 属性来控制行间距
        return f'<p style="color:{color}; margin:0; padding:0; line-height: 1.0;">{text}</p>'

    def update_repeat_run_count_on_ui(self):
        # 更新重复运行次数的显示
        new_text = f"重复运行 ({self.repeat_run_count} 次)"
        self.repeat_checkbox.setText(new_text)


    def update_order_data_on_ui(self):
        # 计算订单数量
        if not os.path.exists('orders_data.json'):
            print("订单数据文件不存在")
            return
        try:
            with open('orders_data.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
            # ... 更新 UI 的代码 ...
        except Exception as e:
            print(f"读取订单数据时发生错误: {e}")
        try:
            with open('orders_data.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # 格式化并更新新订单信息
            new_orders = data.get("NewOrders", [])
            new_orders_text = "<p>".join(
                self.format_text_with_color(
                    f"订单号: {order['order_number']}, 时间: {order['when']}, 类型: {order['service_type']}, 价格: {order['price']}<br>出发地: {order['from']}<br>目的地: {order['to']}<br>",
                    "Turquoise")
                for order in new_orders)
            self.new_orders_text.setHtml(new_orders_text)  # 使用 new_orders_text 变量
            

            # 格式化并更新已接订单信息
            received_orders = data.get("ReceivedOrders", [])
            received_orders_text = "<p>".join(
                self.format_text_with_color(
                    f"订单号: {order['order_number']}, 时间: {order['when']}, 类型: {order['service_type']}, 价格: {order['price']}<br>出发地: {order['from']}<br>目的地: {order['to']}<br>",
                    "Gold")
                for order in received_orders)
            self.received_orders_text.setHtml(received_orders_text)


            # 格式化并更新待接订单信息
            confirmed_orders = data.get("ConfirmedOrders", [])
            confirmed_orders_text = "<p>".join(
                self.format_text_with_color(
                    f"订单号: {order['order_number']}, 时间: {order['when']}, 类型: {order['service_type']}, 价格: {order['price']}<br>出发地: {order['from']}<br>目的地: {order['to']}<br>",
                    "Cyan")
                for order in confirmed_orders)
            self.confirmed_orders_text.setHtml(confirmed_orders_text)


            # 计算每种类型订单的数量
            new_orders_count = len(data.get("NewOrders", []))
            received_orders_count = len(data.get("ReceivedOrders", []))
            confirmed_orders_count = len(data.get("ConfirmedOrders", []))

            # 更新标题标签的文本以显示订单数量
            self.new_orders_label.setText(f"新订单 ({new_orders_count})")
            self.received_orders_label.setText(f"已接订单 ({received_orders_count})")
            self.confirmed_orders_label.setText(f"可接订单 ({confirmed_orders_count})")


        except Exception as e:
            print(f"读取订单数据时发生错误: {e}")


    def update_clock(self):
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.clock_label.setText(current_time)




# 在需要开始处理订单的地方调用 process_orders_and_update_ui
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        main_window = OrderManagementApp()
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"运行时发生错误: {e}")
