# coding=utf-8

import requests
from bs4 import BeautifulSoup as bs
import time
import datetime
from aip import AipOcr
import cv2 as cv
from PIL import Image
import base64
from city_id import city_id
from wxpy import *
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class SDUFE:

    def __init__(self, is_student, user, pwd, name, wxname, sex, phone, p_phone, addr, pid, cid, today, bot, max_time):
        if is_student:
            self.status_1 = "Student"
            self.status_2 = "student"
            self.title = "同学"
        else:
            self.status_1 = "Teacher"
            self.status_2 = "teacher"
            self.title = "老师"
        self.URL = f"http://bcfl.sdufe.edu.cn/{self.status_1}/handle_login"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        self.session = self._init_session()
        self.user = str(user)
        self.pwd = str(pwd)
        self.name = str(name)
        self.wxname = str(wxname)
        self.gender = str(sex)
        self.sex = "1" if "男" in self.gender else "0"
        self.phone = str(phone)
        self.p_phone = str(p_phone)
        self.addr = str(addr)
        self.pid = str(pid)
        self.cid = str(cid)
        self.today = str(today)
        self.image_path = './verify.png'
        self.general = False
        self.APP_ID = 'xxx'
        self.API_KEY = 'xxx'
        self.SECRET_KEY = 'xxx'
        self.max_time = int(max_time)
        self.level = 1
        self.message = self.name + self.title + "："
        self.bot = bot
        self.to = self.send_bot()
        # self.me = self.bot.file_helper

    def send_bot(self):
        try:
            found = self.bot.friends().search(self.name)
            to = ensure_one(found)
        except:
            try:
                found = self.bot.friends().search(self.wxname)
                to = ensure_one(found)
            except:
                to = self.bot.file_helper
        return to

    def _init_session(self):
        session = requests.session()
        session.headers = self.get_headers()
        return session

    def get_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;"
            "q=0.8,application/signed-exchange;"
            "v=b3;"
            "q=0.9",
            "Connection": "keep-alive"}

    def get_session(self):
        return self.session()

    def get_cookies(self):
        return self.get_session().cookies

    def get_verify(self):
        url = "http://bcfl.sdufe.edu.cn/index.php"
        params = {
            "g": "api",
            "m": "checkcode",
            "a": "index",
            "time": "0." + str(int(time.time()*100000000000))[4:]
        }
        headers = self.get_headers()
        resp = self.session.get(url=url, headers=headers, params=params)
        if resp.status_code != requests.codes.OK:
            print(self.user + "：验证码页面获取失败！")
            self.message += self.user + "：验证码页面获取失败！"

        with open(self.image_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024):
                f.write(chunk)

    def cut_image(self, p=0.6):
        img = cv.imread(self.image_path)
        cutted = img[0: img.shape[0], 0: int(img.shape[1] * p), :]
        cv.imwrite(self.image_path, cutted)

    def cut_and_enhance(self):
        self.cut_image(p=1)
        src = cv.imread(self.image_path)
        # 边缘保留滤波  去噪
        blur = cv.pyrMeanShiftFiltering(src, sp=8, sr=60)
        # 灰度图像
        gray = cv.cvtColor(blur, cv.COLOR_BGR2GRAY)
        # 二值化：设置阈值，自适应阈值的话，黄色的 4 会提取不出来
        _, binary = cv.threshold(gray, 185, 255, cv.THRESH_BINARY_INV)
        # 逻辑运算：让背景为白色，字体为黑色，便于识别
        cv.bitwise_not(binary, binary)
        cv.imwrite(self.image_path, binary)

    def baidu_ocr(self):
        self.cut_image()
        data = {
            "grant_type": "client_credentials",
            "client_id": self.API_KEY,
            "client_secret": self.SECRET_KEY
        }
        token_url = "https://aip.baidubce.com/oauth/2.0/token"
        token = requests.post(token_url, data=data).json()
        access_token = token["access_token"]
        with open(self.image_path, 'rb') as f:
            img = base64.b64encode(f.read())
        if self.general:
            number_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
            params = {"image": img, "detect_direction": "true",
                      "language_type": "KOR"}
        else:
            number_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/numbers"
            params = {"image": img, "detect_direction": "true"}
        request_url = number_url + "?access_token=" + access_token
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(
            request_url, data=params, headers=headers).json()
        if "error_code" in response:
            if str(response["error_code"]) == "17" and self.level == 1:
                print("change line 2")
                self.APP_ID = 'xxx'
                self.API_KEY = 'xxx'
                self.SECRET_KEY = 'xxx'
                self.level += 1
            elif str(response["error_code"]) == "17" and self.level == 2:
                print("change general mode")
                self.general = True
                self.max_time += 10
            number = "error_code = 17"
        else:
            if response["words_result"]:
                number = response["words_result"][-1]["words"]
            else:
                number = "there is no 'words_result'"
        try:
            str(number)
        except:
            number = "0"
        number = ''.join(number.split())
        return number

    def login(self):
        number_1 = "0"
        while (len(number_1) < 4 or not number_1.isdigit()) and self.max_time > 0:
            self.get_verify()
            # text = self.recognize_text()
            number_1 = self.baidu_ocr()
            print(number_1)
            self.max_time -= 1
        print(number_1)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*;"
                      "q=0.01",
            "Connection": "keep-alive",
            "Referer": "http://bcfl.sdufe.edu.cn/Index/login?from=groupmessage",
            "Content-Type": "application/x-www-form-urlencoded;"
                            "charset=UTF-8"}
        data = {
            "number": self.user,
            "card": self.pwd,
            "verify": number_1
        }
        resp = self.session.post(
            url=self.URL, headers=headers, data=data).json()
        print(resp)
        if resp and self.max_time >= 0:
            if resp['msg'] == "登陆成功！":
                print("登陆成功了啊！")
                return True
            else:
                return False
        elif self.max_time < 0:
            self.message += "\n1. 登陆失败，验证码使用次数达到了上限（每人 10 次），请手动打卡吧。"
            return False
        else:
            return False

    def result(self):
        number_2 = "0"
        while (len(number_2) < 4 or not number_2.isdigit()) and self.max_time > 0:
            self.get_verify()
            number_2 = self.baidu_ocr()
            self.max_time -= 1
        print(number_2)
        post_url = f"http://bcfl.sdufe.edu.cn/{self.status_1}/handle_ext_do"
        post_data = {
            "name": self.name,
            "sex": self.sex,
            "study_id": self.user,
            "college_id": "408",
            "address": self.addr,
            "contact": self.phone,
            "phone": self.p_phone,
            "province_id": self.pid,
            "city_id": self.cid,
            "now_address": self.addr,
            "now_status": "1",
            "now_status_msg": "",
            "partition_time": "",
            "behavior": "1",
            "travel_address": "",
            "back_address": "",
            "travel_start": "",
            "travel_back": "",
            "travel_type": "0",
            "travel_number": "",
            "is_public": "0",
            "country_travel": "0",
            "travel_msg": "",
            "other_msg": "",
            "verify": number_2
        }
        post_resp = self.session.post(url=post_url, data=post_data).json()
        print(post_resp)
        if post_resp and self.max_time >= 0:
            if post_resp['msg'] == "签到成功":
                print("签到成功了啊")
                return True
            else:
                return self.result()
        elif self.max_time < 0:
            self.message += "\n2. 提交失败，验证码使用次数达到了上限（每人 10 次），请手动打卡吧。"
            return False
        else:
            return self.result()

    def full_process(self):
        login = self.login()
        while not login and self.max_time > 0:
            print(self.max_time)
            print(login)
            login = self.login()
        if not login and self.max_time <= 0:
            self.message += "\n登陆失败啦！\n自动打卡可能失败，请手动登陆查看！\n（本信息为程序自动发送，无需回复）"
            return self.message
        self.message += "\n1. 登陆成功！"
        home_url = f"http://bcfl.sdufe.edu.cn/{self.status_1}/handle_person"
        self.session.get(url=home_url)
        daka_url = f"http://bcfl.sdufe.edu.cn/{self.status_2}/handle_ext.html"
        self.session.get(url=daka_url)
        post_result = self.result()
        while not post_result and self.max_time > 0:
            print(self.max_time)
            print(post_result)
            post_result = self.result()
        if not post_result and self.max_time <= 0:
            self.message += "\n提交失败啦！\n自动打卡可能失败，请手动登陆查看！\n（本信息为程序自动发送，无需回复）"
            return self.message
        self.message += "\n2. 提交成功！"
        result_url = f"http://bcfl.sdufe.edu.cn/{self.status_1}/handle_health"
        try:
            result_resp = self.session.get(url=result_url).text
            soup = bs(result_resp, 'lxml')
            result = soup.select("ul.info-list-up>li>span")
            if result:
                today = result[0].text
            else:
                today = str(result)
        except:
            today = None
        if post_result and today == self.today:
            self.message += f"\n\n恭喜你，今天（{self.today}）的打卡成功了！\n（本信息为程序自动发送，无需回复）"
        elif self.max_time <= 0:
            self.message += "\n\n打卡失败，验证次数用尽，请手动登陆看看打卡是否成功。\n（本信息为程序自动发送，无需回复）"
        else:
            self.message += "\n\n打卡失败（最后一步出错了），请手动登陆看看打卡是否成功。\n（本信息为程序自动发送，无需回复）"
        return self.message

    def daka(self):
        msg = self.full_process()
        self.to.send(msg)
        # self.me.send(msg)

    def debug(self):
        self.get_verify()
        number_1 = self.baidu_ocr()
        print(number_1)


if __name__ == "__main__":
    bot = Bot(console_qr=1)
    while True:
        hour = time.strftime("%H")
        if str(hour) == "22":
            with open("./list.txt", encoding="utf-8") as f:
                students = f.readlines()
            for student in students:
                text = student.strip().split()
                status = text[0]
                if "#" in status:
                    continue
                if '学生' in status:
                    is_student = True
                else:
                    is_student = False
                name = text[1]
                wxname = text[2]
                sex = text[3]
                user = text[4]
                pwd = text[5]
                phone = text[6]
                p_phone = text[7]
                province = text[8]
                pid = 16 if "山东" in province else 16
                city = text[9]
                if '市' not in city and len(city) < 3:
                    city += "市"
                cid = city_id[city]
                addr = text[10]
                max_time = str(text[11])
                today = datetime.date.today().strftime('%m-%d')
                sdufe = SDUFE(is_student, user, pwd, name, wxname, sex,
                              phone, p_phone, addr, pid, cid, today, bot, max_time)
                sdufe.daka()
                sdufe = ""
                time.sleep(5)
            time.sleep(23 * 60 * 60)
        time.sleep(10 * 60)
        bot.join()
