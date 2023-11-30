
#order_processsing.py
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from datetime import datetime, time
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementNotInteractableException
import os
from selenium.common.exceptions import StaleElementReferenceException
import json
import re

# 全局变量定义
received_orders_box = []

def get_booked_orders(driver):
    global received_orders_box
    # ... 函数实现 ...

# process_orders 函数
def process_orders():
    global received_orders_box

    # WebDriver 初始化
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(executable_path="/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    import time

    # 查找名为 'Elife Driver App' 的标签页
    found = False
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if driver.title == 'Elife Driver App':
            print("已切换到 'Elife Driver App' 标签页。")
            found = True
            break

    if not found:
        print("未找到 'Elife Driver App' 标签页。")
    else:
        while True:
            try:
                # 等待 "loading..." 指示器消失
                element_present = WebDriverWait(driver, 3).until_not(
                    EC.presence_of_element_located((By.ID, "loading-wrapper"))
                )
                if not element_present:
                    # 如果页面未完成加载，则刷新
                    driver.refresh()

                # 给页面额外的时间来完成所有的动态加载

                time.sleep(3)
                # 等待 "loading..." 指示器消失
                element_present = WebDriverWait(driver, 3).until_not(
                    EC.presence_of_element_located((By.ID, "loading-wrapper"))
                )
                # 检查是否存在包含 "Sorry, no rides now." 的元素
                no_rides_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Sorry, no rides now.')]")
                if no_rides_elements and no_rides_elements[0].is_displayed():
                    print("页面上显示 'Sorry, no rides now.', 将继续刷新...")
                    driver.refresh()
                    continue

                # 检查新订单列表是否开始加载
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='bid-rides-list-row-']"))
                )
                time.sleep(2)
                print("网页已经加载完成，找到了订单列表。")
                break
            except TimeoutException:
                print("等待超时 - 网页未能在指定时间内加载完毕，重新刷新页面")




    # ---------------------------------------------------------------定义容器存储新订单信息----------------------------------------------------------------------#
    new_orders_box = []

    # 函数：从页面读取订单并提取信息
    def get_orders_from_page(driver):
    # 遍历订单列表
        for index in range(1, 50):  # 假设最多50个新订单
            try:
                # 使用JavaScript找到订单元素
                order_element = driver.execute_script(
                    "return document.getElementById('bid-rides-list-row-" + str(index) + "');"
                )

                # 如果订单元素存在，提取信息
                if order_element:
                    order_number = driver.execute_script(
                        "return arguments[0].querySelector('button.accept-act[data-ride-id]').getAttribute('data-ride-id');", 
                        order_element
                    )
                    from_name_text = driver.execute_script(
                        "return arguments[0].querySelector('div.addr[name=\"from-name\"]').textContent;", 
                        order_element
                    )
                    to_name_text = driver.execute_script(
                        "return arguments[0].querySelector('div.addr[name=\"to-name\"]').textContent;", 
                        order_element
                    )
                    when_text = driver.execute_script(
                        "return arguments[0].querySelector('span.when[name=\"when\"]').textContent;", 
                        order_element
                    )
                    fund_text = driver.execute_script(
                        "return arguments[0].querySelector('div.fund[name=\"fund\"]').textContent;", 
                        order_element
                    )
                    service_type = "送机" if any(airport in to_name_text for airport in ["Haneda", "羽田","Narita", "成田","HND", "NRT"]) else "接机"

                    order_info = {
                        'order_number': order_number,
                        'from': from_name_text,
                        'to': to_name_text,
                        'when': when_text,
                        'service_type': service_type,
                        'price': fund_text
                    }

                    new_orders_box.append(order_info)

                    # 格式化并打印新订单信息
                    print(f"读取到新订单:\n"
                        f"订单号: {order_info['order_number']}\n"
                        f"时间: {order_info['when']}\n"
                        f"类型: {order_info['service_type']}\n"
                        f"价格: {order_info['price']}\n")

            except TimeoutException:
                # 如果找不到元素，结束循环
                print(f"新订单 {index} 未出现，结束读取。")
                break
            except Exception as e:
                print(f"获取订单信息时出错：{e}")
                continue

    # 调用函数获取订单信息
    get_orders_from_page(driver)
    print(f"共有 {len(new_orders_box)} 个新订单读取完成")

    #---------------------------------------------------------------------获取新订单列信息完成并保存到new_orders_box---------------------------------------------------------------------#


    #---------------------------------------------------------------------检查订单是否符合条件并保存到first_filter_box---------------------------------------------------------------------#
    # 组合筛选函数：检查订单是否满足所有条件
    # 函数：将时间字符串转换为24小时制格式并删除AM/PM
    from datetime import datetime, time

    def format_time_24hr(time_str):
        # 删除 AM 和 PM
        return time_str.replace(' AM', '').replace(' PM', '').strip()

    def check_all_conditions(order):
        # 检查价格
        try:
            fund_value = float(order['price'].split(' ')[1].replace(",", ""))
            if fund_value < 1:
                print(f"订单号:{order['order_number']}不符合条件,原因:价格小于6200")
                return False
        except (IndexError, ValueError) as e:
            print(f"订单号:{order['order_number']}不符合条件,原因:价格解析错误 - {e}")
            return False

        # 检查目的地是否包含 Narita 或 NRT
        if "Narita" in order['from'] or "NRT" in order['from'] or "成田" in order['from'] or "Narita" in order['to'] or "成田" in order['to'] or "NRT" in order['to']:
            print(f"订单号:{order['order_number']}不符合条件\n原因:目前设定不接成田单")
            return False

        # 转换时间格式并检查时间条件
        formatted_time = format_time_24hr(order['when'])
        try:
            order_datetime = datetime.strptime(formatted_time, "%Y-%m-%d %H:%M")
            order_time = order_datetime.time()
            order_weekday = order_datetime.weekday()  # 星期一为 0，星期日为 6
        except ValueError as e:
            print(f"订单号:{order['order_number']}时间格式错误:{e}")
            return False

        # 确定是接机还是送机
        service_type = "送机" if "Haneda" in order['to'] or "HND" in order['to'] or "羽田" in order['to'] else "接机"

        # 根据是否是周末设置时间段
        if order_weekday >= 5:  # 周末
            valid_times = [(time(6, 0), time(20, 0))]
        else:  # 工作日
            if service_type == "接机":
                valid_times = [(time(6, 0), time(8, 0)), (time(17, 0), time(19, 0))]
            else:  # 送机
                valid_times = [(time(6, 30), time(12, 0)), (time(18, 0), time(21, 30))]

        # 检查时间是否在有效时间段内
        is_valid = any(start <= order_time <= end for start, end in valid_times)
        if not is_valid:
            print(f"订单号:{order['order_number']},时间:{order['when']}\n不在指定接单时间内")
            return False

        print(f"订单号:{order['order_number']},时间:{order['when']}\n符合接单所有条件")
        return True

    # 创建 First filter box
    first_filter_box = []

    # 筛选符合所有条件的订单并保存..........
    for order in new_orders_box:
        if check_all_conditions(order):
            first_filter_box.append(order)

    # 打印筛选结果
    print(f"筛选完成。可接订单列表中共有{len(first_filter_box)}个订单符合条件。")


    #----------------------------------------------------新订单记载完成并转化筛选后存储到first_filter_box----------------------------------------------------



    #--------------------------------------------------------------------打开已接订单列表信息----------------------------------------------------

    # 全局变量定义
    received_orders_box = []

    # 切换到已接订单列表页
    def click_booked_orders_button(driver):
        try:
            print("尝试读取已接订单页列表信息...")
            booked_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "orders-booked-act"))
            )
            booked_class = booked_element.get_attribute("class")

            # 检查当前页面状态，并点击按钮以刷新或切换到已接订单列表页
            if "booked cur" in booked_class:
                print("当前页面已经是已接订单列表页，刷新订单列表...")
            else:
                print("当前页面不是已接订单列表页，切换到已接订单列表页...")
            
            booked_element.click()

            import time
            time.sleep(3)
            # 等待已接订单列表页加载完成
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "rides-list-row-1"))
            )


        except TimeoutException:
            print("等待已接订单列表时超时。")
        except Exception as e:
            print(f"切换到已接订单列表页时出现错误：{e}")

    # 调用函数
    click_booked_orders_button(driver)

    import time
    print("新订单列表已加载,下面开始读取已接订单列表...")
    time.sleep(2)  # 等待2秒

    #----------------------------------------------------------------------打开已接订单列表----------------------------------------------------------------

    #----------------------------------------------------读取已接订单列表信息转化时间格式后存储到received_orders_box----------------------------------------------------

    def get_booked_orders(driver):
        global received_orders_box
        received_orders_box.clear()

        index = 1
        Obtained_order = set()  # 用于存储已获取的订单号，防止重复处理
        while True:
            try:
                order_element_id = f"rides-list-row-{index}"
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, order_element_id))
                )

                order_element = driver.find_element(By.ID, order_element_id)

                # 使用JavaScript获取订单信息
                order_number = driver.execute_script(
                    "return arguments[0].querySelector('[name=\"ride-id\"]').textContent.split()[0];",
                    order_element
                )
                # 使用正则表达式提取纯粹的订单号部分
                order_number_only = re.search(r'(\d+-\d+)', order_number).group(1).strip()

                from_name = driver.execute_script(
                    "return arguments[0].querySelector('.from-name .addr').textContent;",
                    order_element
                )
                to_name = driver.execute_script(
                    "return arguments[0].querySelector('.to-name .addr').textContent;",
                    order_element
                )
                when = driver.execute_script(
                    "return arguments[0].querySelector('.when').textContent;",
                    order_element
                )
                price = driver.execute_script(
                    "return arguments[0].querySelector('.fund').textContent;",
                    order_element
                )

                service_type = "送机" if "Haneda" in to_name or "HND" in to_name else "接机"

                # 检查是否重复订单
                if order_number in Obtained_order:
                    continue  # 如果是重复的订单号，跳过本次循环

                Obtained_order.add(order_number)  # 添加订单号到已获取集合


                received_orders_box.append({
                    'order_number': order_number,
                    'from': from_name,
                    'to': to_name,
                    'when': when,
                    'service_type': service_type,
                    'price': price
                })


                # 使用提取的订单号
                print(f"订单号:{order_number_only},类型:{service_type},时间:{when}")
                index += 1


                # 检查是否已经读取了至少19条订单
                if len(received_orders_box) >= 19:
                    next_button = driver.find_element(By.XPATH, '//div[@name="next"]')
                    next_button_style = next_button.get_attribute("style")

                    if "contrast(80%)" not in next_button_style:  # 检查按钮是否可点击
                        next_button.click()  # 点击下一页按钮
                        time.sleep(2)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "rides-list-row-1"))
                        )  # 等待新页面加载
                        index = 1  # 重置索引
                    else:
                        break  # 如果按钮样式表明不可点击，则结束循环

            except TimeoutException:
                print("已读取所有订单，结束")
                break
            except Exception as e:
                print(f"获取订单信息时出错：{e}")
                continue

        print(f"共读取 {len(received_orders_box)} 个订单")

    get_booked_orders(driver)


    #----------------------------------------------------读取已接订单列表信息转化时间格式后存储到received_orders_box----------------------------------------------------



    #----------------------------------------------------------进行核心矩阵规则对比并输出到Confirmed_orders_box---------------------------------------------------


    # 函数：将时间字符串转换为24小时制格式并删除AM/PM
    def format_time_24hr(time_str):
        return time_str.replace(' AM', '').replace(' PM', '').strip()

    # 函数：确保订单时间格式为24小时制
    def ensure_24hr_format(orders):
        for order in orders:
            order['when'] = format_time_24hr(order['when'])

    # 函数：检查两个订单是否在同一天
    def is_same_day(order1, order2):
        date1 = datetime.strptime(order1['when'], "%Y-%m-%d %H:%M").date()
        date2 = datetime.strptime(order2['when'], "%Y-%m-%d %H:%M").date()
        return date1 == date2

    # 函数：确定订单类型
    def determine_order_type(order):
        return 1 if "Haneda" in order['to'] or "HND" in order['to'] else 2

    # 函数：计算时间差
    def time_difference(time1, time2):
        t1 = datetime.strptime(time1, "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(time2, "%Y-%m-%d %H:%M")
        return abs((t2 - t1).total_seconds() / 60)

    # 函数：应用时间矩阵规则
    def apply_time_matrix_rules(new_order, received_orders):
        new_order_time = datetime.strptime(new_order['when'], "%Y-%m-%d %H:%M")
        new_order_type = determine_order_type(new_order)

        for received_order in received_orders:
            if not is_same_day(new_order, received_order):
                continue

            received_order_time = datetime.strptime(received_order['when'], "%Y-%m-%d %H:%M")
            received_order_type = determine_order_type(received_order)

            # 计算时间差
            time_diff_before = time_difference(received_order['when'], new_order['when'])
            time_diff_after = time_difference(new_order['when'], received_order['when'])


            # 应用时间矩阵规则
            if not is_order_acceptable(received_order_type, new_order_type, received_order_type, time_diff_before, time_diff_after):
                return False

        return True

    # 时间矩阵规则检查
    def is_order_acceptable(type_before, new_order_type, type_after, time_diff_before, time_diff_after):
        types = (type_before, new_order_type, type_after)

        # 根据订单类型和时间差，应用不同的规则
        if types == (1, 1, 1):
            return time_diff_before >= 100 and time_diff_after >= 100
        elif types == (1, 1, 2):
            return time_diff_before >= 100 and time_diff_after >= 180
        elif types == (1, 2, 1):
            return time_diff_before >= 180 and (time_diff_after <= -40 or time_diff_after >= 140)
        elif types == (1, 2, 2):
            return time_diff_before >= 180 and time_diff_after >= 80
        elif types == (2, 1, 1):
            return (time_diff_before <= -40 or time_diff_before >= 140) and time_diff_after >= 100
        elif types == (2, 1, 2):
            return (time_diff_before <= -40 or time_diff_before >= 140) and time_diff_after >= 180
        elif types == (2, 2, 1):
            return time_diff_before >= 80 and (time_diff_after <= 80 or time_diff_after >= 140)
        elif types == (2, 2, 2):
            return time_diff_before >= 80 and time_diff_after >= 80
        # 没有前一个订单的情况
        elif type_before is None:
            if new_order_type == 1:  # 接机
                if type_after == 1:
                    return time_diff_after >= 100
                elif type_after == 2:
                    return time_diff_after >= 180
            elif new_order_type == 2:  # 送机
                if type_after == 1:
                    return (time_diff_after <= -40 or time_diff_after >= 140)
                elif type_after == 2:
                    return time_diff_after >= 80
        # 没有后一个订单的情况
        elif type_after is None:
            if new_order_type == 1:  # 接机
                if type_before == 1:
                    return time_diff_before >= 180
                elif type_before == 2:
                    return (-40 <= time_diff_before <= 20) or (time_diff_before > 140)
            elif new_order_type == 2:  # 送机
                if type_before == 1:
                    return time_diff_before >= 140
                elif type_before == 2:
                    return time_diff_before >= 80
        # 前后都无订单的情况
        elif type_before is None and type_after is None:
            # 只需要判断新订单的类型
            if new_order_type == 1:  # 接机
                return True  # 可以接接机订单
            elif new_order_type == 2:  # 送机
                return True  # 可以接送机订单

        return False  # 如果订单不符合任何规则





    # 确保所有订单使用24小时格式
    ensure_24hr_format(first_filter_box)
    ensure_24hr_format(received_orders_box)


    def remove_duplicate_orders(orders):
        unique_orders = {}
        for order in orders:
            order_number = order.get('order_number')
            unique_orders[order_number] = order
        return list(unique_orders.values())

    # 过滤和确认订单
    Confirmed_orders_box = [order for order in first_filter_box if apply_time_matrix_rules(order, received_orders_box)]

    # 去除重复的订单
    Confirmed_orders_box = remove_duplicate_orders(Confirmed_orders_box)

    # 打印确认信息
    for order in Confirmed_orders_box:
        print(f"订单号:{order['order_number']}\n时间:{order['when']},类型:{order['service_type']},价格:{order['price']}已确认并添加到待接订单列表中")

    print(f"共有 {len(Confirmed_orders_box)}个订单通过时间矩阵规则筛选。")

    # 保存到JSON文件
    data_to_write = {
        "ConfirmedOrders": Confirmed_orders_box,
        "ReceivedOrders": received_orders_box,
        "NewOrders": new_orders_box
    }

    with open('orders_data.json', 'w', encoding='utf-8') as file:
        json.dump(data_to_write, file, ensure_ascii=False, indent=4)

    print("可接订单数据保存成功")
