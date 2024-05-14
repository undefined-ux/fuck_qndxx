import json
import sys
from datetime import datetime
from pathlib import Path
import os
import loguru
import requests
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


OPENID_LIST = [
    i for i in os.getenv("QNDXX_OPENID_LIST").split()
    if i
]
# OPENID_LIST = [
#     "ohz9Mt5D4hwhwyZ_d3mn9aHGeENY"
# ]

BASE_URL = "http://qndxx.youth54.cn/SmartLA/dxxjfgl.w?method={}"
headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0"
                  " Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090a13) "
                  "XWEB/9129 Flue",
    'Accept-Encoding': "gzip, deflate",
    'Content-Type': "application/x-www-form-urlencoded",
    'X-Requested-With': "XMLHttpRequest",
    'Origin': "http://qndxx.youth54.cn",
    'Accept-Language': "zh-CN,zh;q=0.9",
}
HTML_CONTENT = open("./web/index.html", "r", encoding="UTF-8").read()


def generate_vue_script(records) -> str:
    return f"""
    var app = new Vue({{
        el: "#main",
        data: {{
            yearselected: {records['selectedyear']},
            options: {records['nfds']},
            record: {{
                "vds": {records['vds']}
            }},
        }}
    }})"""


def __initialize_logger(log_path: str = 'log.log', logger=loguru.logger):
    logger.remove(0)
    logger.add(sys.stderr,
               format="[<green>{time:YYYY-MM-DD HH:mm:ss}</green>] [<level>{level}</level>] <level>{message}</level>")
    logger.add(log_path, format="[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {message}")
    return logger


def get_least_version(openid: str) -> str:
    req = requests.post(BASE_URL.format("getNewestVersionInfo"), headers=headers, data={"openid": openid})
    req_content = req.content.decode("GBK")
    data = json.loads(req_content)
    return data["version"]


def fuck_it(openid: str, least_version: str = None) -> str | None:
    if least_version is None:
        least_version = get_least_version(openid)

    req = requests.post(
        BASE_URL.format("studyLatest"),
        headers=headers,
        data={"openid": openid, "version": least_version}
    )
    data = req.json()

    return None if data["errcode"] == '0' else data["errmsg"]


def get_study_record(openid: str):
    req = requests.post(BASE_URL.format("queryPersonStudyRecord"), headers=headers, data={"openid": openid})
    return req.json()


def screen_shot(save_png_path: str, file_path: str = "./web/out.html"):
    option = webdriver.ChromeOptions()
    option.add_argument("--headless")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=option)
    driver.set_window_size(915, 1294)
    html_path = Path(file_path).absolute()
    driver.get(f"file://{html_path}")
    # print(save_png_path)
    if not driver.save_screenshot(save_png_path):
        # driver.close()
        raise ValueError("Save Failed")


if __name__ == "__main__":
    logger = __initialize_logger()
    for openid in OPENID_LIST:
        logger.info(f"[{openid}] start.")
        version = get_least_version(openid)
        logger.info(f"[{openid}] least_version = {version}")
        if (errmsg := fuck_it(openid, version)) is not None:
            logger.error(f"[{openid}] {errmsg}")
            continue

        logger.info(f"[{openid}] 保存学习记录截图...")
        records = get_study_record(openid)

        screenshot_path = f"./images/{openid}_{datetime.now().date()}.png"
        open("./web/out.html", 'w', encoding="UTF-8").write(
            HTML_CONTENT + f"<script>{generate_vue_script(records)}</script>"
        )
        try:
            screen_shot(screenshot_path, "./web/out.html")
            logger.success(f"[{openid}] 截图路径 {screenshot_path}")
        except:
            logger.error(f"[{openid}] 截图保存失败")
