from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import json
from check_order_acceptance import check_order_acceptance
import time
from selenium.webdriver.common.action_chains import ActionChains

def run_auto_accept():
    # 初始化 WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(executable_path="/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 获取所有标签页的句柄
    window_handles = driver.window_handles
    # 查找名为 'Elife Driver App' 的标签页
    for handle in window_handles:
        driver.switch_to.window(handle)
        if driver.title == 'Elife Driver App':
            print("已切换到 'Elife Driver App' 标签页。")
            break
    else:
        print("未找到 'Elife Driver App' 标签页。")

    # 设置一个循环来不断检查元素是否出现
    while True:
        try:
            # 等待特定元素出现
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@name='title' and contains(text(), 'This list is visible to many fleets')]"))
            )
            print("订单列表页已加载。")
            break  # 如果元素出现了，跳出循环

        except TimeoutException:
            print("等待超时，刷新页面重试。")
            driver.refresh()  # 刷新页面

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='bid-rides-list-row-']"))
    )
    print("页面已经加载。")
    time.sleep(3)

    #设置价格闸值
    price_threshold = 6200
    # 创建一个列表来存储可接订单号
    final_confirmed_orders = []

    with open('orders_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        confirmed_orders = data.get('ConfirmedOrders', [])

    if confirmed_orders:
        print(f"读取到 {len(confirmed_orders)} 条待接订单。")

        for order in confirmed_orders:
            order_number = order.get('order_number')
            print(f"处理订单号: {order_number}")

            # 为每个订单号构建 JavaScript 脚本
            javascript_click_script = f"""
            var orderRows = document.querySelectorAll('.ride-row');
            for (var i = 0; i < orderRows.length; i++) {{
                var rideId = orderRows[i].querySelector('button[data-ride-id]');
                if (rideId && rideId.getAttribute('data-ride-id') === '{order_number}') {{
                    var destinationElement = orderRows[i].querySelector('.addr');
                    if (destinationElement) {{
                        destinationElement.click();
                        break;
                    }}
                }}
            }}
            """
            try:
                # 执行 JavaScript 点击脚本
                driver.execute_script(javascript_click_script)
                print(f"尝试点击订单号: {order_number}")

                # 等待页面加载
                WebDriverWait(driver, 20).until_not(
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'loading')]"))
                )
                try:
                    # 等待直到指定的元素出现在页面上
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".--py-2"))
                    )

                    print("订单详细页面加载完成。")
                    # 在这里执行更多的操作，比如读取元素的信息或点击元素等

                except TimeoutException:
                    print("等待超时 - 页面上没有找到指定的订单号。")

            except TimeoutException:
                print("点击订单号时出现错误,未能进入订单详情页。")

            time.sleep(2)
            with open('var_orders.js', 'r') as file:
                var_orders_script = file.read()

            # 在 WebDriver 中执行 JavaScript 脚本并获取返回值
            script_result = driver.execute_script(var_orders_script)

            # 打印返回的信息
            print("乘客数量: ", script_result["passengerCount"])
            print("司机说明: ", script_result["driverInstruction"])
            print("是否提及婴儿座椅: ", script_result["containsChildKeyword"])
            print("是否合格: ", script_result["isQualified"])


            if script_result["isQualified"]:
                print(f"订单 {order_number} 条件符合，添加到可接订单列表。")
                final_confirmed_orders.append(order_number)

            else:
                print(f"订单 {order_number} 条件不符合。")
                continue

            # 点击返回按钮，返回订单列表
            try:
                return_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "i.i-arrow-left"))
                )
                return_button.click()

                # 等待返回到订单列表页面
                # 等待 "loading..." 指示器消失
                WebDriverWait(driver, 20).until_not(
                    EC.presence_of_element_located((By.ID, "loading-wrapper"))
                )

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".tab-body"))
                )
                print("已返回订单列表页")

            except TimeoutException:
                print("找不到或无法点击返回按钮。")

            # 等待短暂时间后继续下一个订单
            time.sleep(2)

            # 等待 "loading..." 指示器消失
            WebDriverWait(driver, 20).until_not(
                EC.presence_of_element_located((By.ID, "loading-wrapper"))
            )

    else:
        print("没有读取到待接订单,刷新页面的并等待新新订单加载")


    # 获取所有标签页的句柄
    window_handles = driver.window_handles

    # 查找名为 'Elife Driver App' 的标签页
    for handle in window_handles:
        driver.switch_to.window(handle)
        if driver.title == 'Elife Driver App':
            print("已切换到 'Elife Driver App' 标签页。")
            break
    else:
        print("未找到 'Elife Driver App' 标签页。")
        # 可以选择是否退出程序
        # exit(1)

    # 刷新页面
    driver.refresh()
    print("页面已刷新。")

    # 等待直到特定元素出现，如果未出现则再次刷新页面
    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "orders-available-act"))
        )
        print("页面加载完成。")
    except TimeoutException:
        print("等待超时，重新刷新页面。")
        driver.refresh()
        # 这里可以再次等待元素出现或继续后续操作

    for order_number in final_confirmed_orders:
        print(f"正在处理订单号为 {order_number} 的订单...")

        try:
            price_matched = False
            for i in range(1, 21):  # 假设每页最多20个订单
                try:
                    ride_id_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"#bid-rides-list-row-{i} [data-ride-id]"))
                    )
                    if ride_id_element.get_attribute("data-ride-id") == order_number:
                        price_element = driver.find_element(By.CSS_SELECTOR, f"#bid-rides-list-row-{i} .fund")
                        price_text = price_element.text.strip()
                        if "JPY" in price_text:
                            price = float(price_text.split()[1])
                            if price < price_threshold:
                                print(f"订单 {order_number} 的价格 {price} 低于阈值 {price_threshold}，跳过此订单。")
                            else:
                                price_matched = True
                            break
                except TimeoutException:
                    continue  # 如果在当前订单元素中找不到价格，检查下一个订单元素

            if not price_matched:
                continue  # 如果未找到匹配的订单或价格低于阈值，处理下一个订单

            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[data-ride-id='{order_number}']"))
            )
            accept_button.click()
            print(f"订单 {order_number} 的接受按钮已点击。")


            # 检查是否出现了确认弹窗
            try:
                confirm_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Yes']"))
                )
                confirm_button.click()
                print(f"订单 {order_number} 的Yes按钮已点击。")

                time.sleep(3)

                # 等待带有'loading'文本的弹窗消失
                WebDriverWait(driver, 20).until_not(
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'loading')]"))
                )
                print(f"订单 {order_number} 的'loading'弹窗已消失。")


                # 等待带有'congratulations'文本的弹窗消失
                WebDriverWait(driver, 20).until_not(
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'congratulations')]"))
                )
                print(f"订单 {order_number} 的'congratulations'弹窗已消失。")


            except TimeoutException:
                print(f"未出现确认弹窗，检查是否进入了其他界面。")
                
                # 新增加的检查特定页面的代码
                around_rides_title_xpath = "//*[contains(text(),'Accepted rides around the same time')]"
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, around_rides_title_xpath))
                    )
                    print("已进入‘Accepted rides around the same time’页面。")

                    # 找到并点击接受按钮
                    accept_button_xpath = "//div[contains(@class, '--cursor-pointer') and contains(text(), 'Accept')]"
                    accept_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, accept_button_xpath))
                    )
                    driver.execute_script("arguments[0].click();", accept_button)
                    print("已点击接受按钮。")

                    # 等待带有'loading'文本的弹窗消失
                    WebDriverWait(driver, 20).until_not(
                        EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'loading')]"))
                    )
                    print(f"订单 {order_number} 的'loading'弹窗已消失。")

                    # 等待带有'congratulations'文本的弹窗消失
                    WebDriverWait(driver, 20).until_not(
                        EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'congratulations')]"))
                    )
                    print(f"订单 {order_number} 的'congratulations'弹窗已消失。")

                except TimeoutException:
                    print("未找到‘Accepted rides around the same time’相关元素或等待超时。")


        except TimeoutException:
            print(f"订单 {order_number} 的接受按钮未出现或等待超时。")

