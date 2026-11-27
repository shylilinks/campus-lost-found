# -*- coding: utf-8 -*-
"""A1 v2: Selenium 端到端测试（修复 confirm 弹窗处理、注册断言、匹配断言）"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(r"C:\Users\15633\Desktop\软件测试与质量保证课程实验\实验工作区")
ROOT = BASE / "campus-lost-found"
PORT = int(os.environ.get("PORT", "5001"))
BASE_URL = f"http://127.0.0.1:{PORT}"
HEADLESS = os.environ.get("E2E_HEADLESS") == "1"

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

results = []
shots = ROOT / "截图" / "端到端测试"
shots.mkdir(parents=True, exist_ok=True)


def record(case, passed, note=""):
    results.append((case, "通过" if passed else "失败", note))
    print(("✅" if passed else "❌"), case, note)


def disable_alerts(driver):
    driver.execute_script("window.confirm = () => true; window.alert = () => true;")


def run_flow():
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,950")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    uid = time.strftime("2025%H%M%S")  # 每次运行唯一学号

    steps_run = []

    def step(name, fn):
        # 每步独立 try，失败记录但继续后面的步骤
        try:
            fn()
        except Exception as e:
            record(name, False, f"{type(e).__name__}: {str(e)[:80]}")
            driver.save_screenshot(str(shots / f"fail_{len(results)}.png"))
        steps_run.append(name)

    def s_register():
        driver.get(f"{BASE_URL}/register")
        driver.find_element(By.NAME, "uid").send_keys(uid)
        driver.find_element(By.NAME, "name").send_keys("端到端测试同学")
        driver.find_element(By.NAME, "pwd").send_keys("test123456")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "hero-tip")))
        ok = "端到端测试同学" in driver.page_source and "退出" in driver.page_source
        record("注册：用学号注册并自动登录", ok, "导航栏显示姓名与退出链接")
        driver.save_screenshot(str(shots / "e2e_1_register.png"))

    def s_login():
        driver.get(f"{BASE_URL}/logout")
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.NAME, "uid").send_keys(uid)
        driver.find_element(By.NAME, "pwd").send_keys("test123456")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "hero-tip")))
        ok = "退出" in driver.page_source
        record("登录：退出后重新登录", ok)
        driver.save_screenshot(str(shots / "e2e_2_login.png"))

    def s_publish():
        driver.get(f"{BASE_URL}/publish")
        driver.find_element(By.NAME, "type").send_keys("lost")
        driver.find_element(By.NAME, "title").send_keys("黑色钢笔（E2E）")
        driver.find_element(By.NAME, "category").send_keys("其他")
        driver.find_element(By.NAME, "desc").send_keys("在9栋教学楼502丢了一支黑色钢笔，笔帽有金属环")
        driver.find_element(By.NAME, "location").send_keys("9栋教学楼502")
        d = driver.find_element(By.NAME, "date")
        driver.execute_script("arguments[0].value = arguments[1]", d, time.strftime("%Y-%m-%d"))
        driver.find_element(By.NAME, "contact").send_keys("QQ 999888777")
        shot = shots / "e2e_2_login.png"
        if shot.exists():
            driver.find_element(By.NAME, "photo").send_keys(str(shot))
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        ok = "黑色钢笔（E2E）" in driver.page_source
        record("发布：登记失物（含照片上传）后跳转详情页", ok)
        driver.save_screenshot(str(shots / "e2e_3_publish.png"))

    def s_search():
        driver.get(f"{BASE_URL}/?q=钢笔")
        time.sleep(1)
        ok = "黑色钢笔（E2E）" in driver.page_source
        record("搜索：首页搜索“钢笔”能找到刚发布的记录", ok)

    def s_matches():
        driver.get(f"{BASE_URL}/matches/1")
        time.sleep(1)
        ok = "智能匹配推荐" in driver.page_source
        record("匹配：智能匹配页正常渲染", ok)

    def s_chat():
        driver.get(f"{BASE_URL}/chat/1")
        disable_alerts(driver)
        driver.find_element(By.ID, "text").send_keys("E2E 测试留言：你好！")
        driver.find_element(By.CSS_SELECTOR, "#chat-input button").click()
        time.sleep(1.5)
        ok = "E2E 测试留言" in driver.page_source
        record("留言：私聊窗口发送留言并显示", ok)
        driver.save_screenshot(str(shots / "e2e_4_chat.png"))

    def s_resolve():
        driver.get(f"{BASE_URL}/item/1")
        disable_alerts(driver)
        btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form[action*='resolve'] button")))
        btn.click()
        time.sleep(1.5)
        ok = "已解决" in driver.page_source or "已找回" in driver.page_source
        record("状态：标记已找回后显示已解决徽标", ok)
        driver.save_screenshot(str(shots / "e2e_5_resolve.png"))

    def s_filter():
        driver.get(f"{BASE_URL}/?type=resolved")
        time.sleep(1)
        ok = "已解决" in driver.page_source
        record("筛选：已解决 Tab 正常显示", ok)

    step("注册：用学号注册并自动登录", s_register)
    step("登录：退出后重新登录", s_login)
    step("发布：登记失物（含照片上传）后跳转详情页", s_publish)
    step("搜索：首页搜索能找到刚发布的记录", s_search)
    step("匹配：智能匹配页正常渲染", s_matches)
    step("留言：私聊窗口发送留言并显示", s_chat)
    step("状态：标记已找回后显示已解决徽标", s_resolve)
    step("筛选：已解决 Tab 正常显示", s_filter)

    try:
        driver.quit()
    except Exception:
        pass


# 启动独立测试服务器
env = dict(os.environ, PORT=str(PORT))
server = subprocess.Popen([sys.executable, "app.py"], cwd=str(ROOT), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(3)
try:
    run_flow()
finally:
    server.terminate()

passed = sum(1 for r in results if r[1] == "通过")
lines = [
    "# Web 平台端到端（E2E）测试报告",
    "",
    "- 测试对象：本平台（Flask 应用）",
    "- 测试工具：Selenium（Chrome，有头模式）",
    f"- 用例总数：{len(results)}　通过：{passed}　失败：{len(results) - passed}",
    "",
    "| 编号 | 测试内容 | 结论 | 备注 |",
    "| --- | --- | --- | --- |",
]
for i, (case, verdict, note) in enumerate(results, 1):
    lines.append(f"| {i} | {case} | {verdict} | {note} |")
lines.append("")
lines.append("覆盖流程：注册 → 登录 → 发布（含照片上传）→ 搜索 → 匹配 → 留言 → 标记找回 → 筛选。")
(ROOT / "e2e_report.md").write_text("\n".join(lines), encoding="utf-8")
print(f"\nE2E 报告已生成：e2e_report.md（{passed}/{len(results)} 通过）")
sys.exit(0 if passed == len(results) else 1)
