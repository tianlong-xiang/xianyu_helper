import json
import re
import sys
import time
import easyocr
import windows
import win32gui
import utils
import cv2
from feishu import FeiShutalkChatbot
import numpy as nm
from datetime import datetime
from loguru import logger
from PIL import ImageGrab, Image
from loguru import logger


class xianyu:

    def __init__(self, ocr_reader):
        """初始化"""

        self.feishu = FeiShutalkChatbot(
            "https://open.feishu.cn/open-apis/bot/v2/hook/79129e41-d4f3-429a-8963-ba04a4dcf4ed")

        # 获取句柄
        self.hwnd = windows.find_hwd("Chrome_WidgetWin_0", "咸鱼之王")

        # 读取题库
        self.ans = []
        self.read_ans("data/ans.txt")

        # 窗口坐标
        self.left, self.top, self.right, self.bottom = 0, 0, 0, 0

        # 获取窗口左上角和右下角坐标
        self.left, self.top, self.right, self.bottom = windows.get_window_pos(
            self.hwnd)
        logger.info("咸鱼之王屏幕坐标：{} {} {} {}", self.left,
                    self.top, self.right, self.bottom)

        # 设置为前台
        # win32gui.SetForegroundWindow(self.hwnd)

        # 公用OCR，初始化太慢
        self.reader = ocr_reader

    def read_ans(self, file_name):
        """读取答案"""
        with open(file_name, 'r', encoding="utf-8") as f:

            content = f.read()
            content = content.split("\n")

            for item in content:
                try:
                    js = json.loads(item)

                    if js['ans'] == 'A':
                        js['ans'] = js['a'][0]
                    if js['ans'] == 'B':
                        js['ans'] = js['a'][1]

                    self.ans.append(js)
                except Exception as e:
                    logger.debug(e)

            logger.info("读取题库：{}", len(self.ans))

    def get_task(self):
        """识别当前任务"""

    def task_auto_answer(self):
        """自动答题"""

        while True:
            # 读取题目
            img = ImageGrab.grab(
                bbox=(self.left+25, self.top+141, self.left+25 + 419, self.top+141 + 130))

            # 设置偏色，提高识别度
            for i in range(img.width):
                for j in range(img.height):
                    try:
                        r, g, b = img.getpixel((i, j))
                        color_set = [[48, 48, 48, 32], [82, 31, 26, 40]]
                        for color in color_set:
                            if color[0] - color[3] < r < color[0] + color[3] and color[1] - color[3] < g < color[1] + color[3] and color[2] - color[3] < b < color[2] + color[3]:
                                img.putpixel((i, j), (0, 0, 0))
                                break
                            else:
                                img.putpixel((i, j), (255, 255, 255))
                    except Exception as e:
                        logger.warning(e)
                        continue

            result = self.reader.readtext(nm.array(img))

            question_str, question_str_old = "", ""
            for item in result:
                question_str += item[1] + ""

            # 去除空格
            question_str = question_str.replace(" ", "")

            # 识别题目不变，无需操作
            if question_str != question_str_old:
                question_str_old = question_str

                similar = 0
                # 最低相似度
                min_similar = 0.6
                result = {}

                # 识别答案，相似度最高的
                for item in self.ans:
                    ret = utils.stri_similar(question_str, item['q'])
                    if ret > similar:
                        # 更新相似度
                        result = item
                        similar = ret

                logger.debug("题目识别结果：{}, 相似度：{}", question_str, similar)
                if len(result) > 0:
                    logger.info("题库对比：{}，答案：{}", result['q'], result['ans'])

                # 相似度低于最低值，不做操作
                if similar > min_similar:
                    #file_name = time.strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"
                    #img.save('data/' + file_name)

                    if (result['ans'] == '对'):
                        windows.left_click_position(self.hwnd, 166, 930, 0.02)
                    if (result['ans'] == '错'):
                        windows.left_click_position(self.hwnd, 422, 923, 0.02)

            time.sleep(0.2)

    def task_auto_pass(self):
        """自动过关"""

        # 计算关卡位置
        (x1, y1) = win32gui.ClientToScreen(self.hwnd, (250, 185))
        (x2, y2) = win32gui.ClientToScreen(self.hwnd, (353, 223))

        game_level = 0
        time_start = datetime.now()

        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        result = self.reader.readtext(cv2.cvtColor(
            nm.array(img), cv2.COLOR_BGR2GRAY))
        if len(result) > 0:
            game_level = result[0][1]
            game_level = re.sub("\D", "", game_level)
            logger.info("启动脚本，检测当前关卡：{}", game_level)

        loop_count = 0
        while True:
            loop_count = loop_count + 1
            if loop_count % 100 == 0:
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                result = self.reader.readtext(cv2.cvtColor(
                    nm.array(img), cv2.COLOR_BGR2GRAY))

                if len(result) > 0:
                    new_game_level = result[0][1]
                    # 仅保留数字
                    new_game_level = re.sub("\D", "", new_game_level)

                if len(new_game_level) <= 0: 
                    continue
                # 推进的关卡数量
                level_count = int(new_game_level) - int(game_level)
                # 前台挂机：关卡递增是有序的; 后台挂机：关卡递增是无序的，兼容识别异常的情况
                if  int(new_game_level) == int(game_level) + 1 or (level_count > 0 and level_count < 1000):
                    # 计算消耗的时间 单位 分钟，保留两位小数
                    time_cost = round(
                        (datetime.now() - time_start).seconds / 60 / level_count, 2)
                    time_start = datetime.now()
                    logger.info("关卡：{}，进度：{}，平均耗时：{} 分钟", new_game_level, level_count, time_cost)
                    self.feishu.send_interactive(
                        "推图进度", "当前关卡：{} 关\n推进数量：{}\n平均耗时：{} 分钟".format(game_level, level_count, time_cost))
                    game_level = new_game_level

            windows.left_click_position(self.hwnd, 299, 783, 0.01)
            windows.left_click_position(self.hwnd, 308, 971, 0.01)


    def task_auto_tower(self):
        loop_count = 0
        while True:
            windows.left_click_position(self.hwnd, 302,1018, 0.01)
            windows.left_click_position(self.hwnd, 73,971, 0.01)
            # 此位置不能一直点击，会导致无法进入下一个步骤
            # 每循环 100此，点击一次
            loop_count = loop_count + 1
            if loop_count % 10 == 0:
                windows.left_click_position(self.hwnd, 304,760, 0.01)

                # 计算关卡位置
                (x1, y1) = win32gui.ClientToScreen(self.hwnd, (215, 340))
                (x2, y2) = win32gui.ClientToScreen(self.hwnd, (396, 606))
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                result = self.reader.readtext(cv2.cvtColor(nm.array(img), cv2.COLOR_BGR2GRAY))
                for item in result:
                    logger.debug(item)
                    if item[1].find('奖励') > 0 and item[1].find('领取') > 0:
                        logger.info("薅羊毛成功")
                        windows.left_click_position(self.hwnd, 55,1021, 2)
                        windows.left_click_position(self.hwnd, 311,333, 2)
                        break
                    if item[1].find('鱼干') > 0:
                        logger.info("小鱼干不足，结束推塔")
                        sys.exit()

    def task_auto_fish(self):
        '''按照坐标直接来，延迟多点，问题不大，比我手动来省事'''
        while True:
            logger.info("Task auto fish running")
            windows.left_click_position(self.hwnd, 170,884, 1.5)
            windows.left_click_position(self.hwnd, 464,603, 1.5)
            windows.left_click_position(self.hwnd, 308,706, 1.5)
            # 等中间的钓鱼动画
            time.sleep(8)
            windows.left_click_position(self.hwnd, 301,943, 1.5)
            # 等鱼钩收集动画
            time.sleep(5)


if __name__ == '__main__':
    # 默认不启用GPU，费电
    xianyu = xianyu(easyocr.Reader(['ch_sim', 'en'], gpu=False))
    # 自动推图
    # xianyu.task_auto_pass()
    # 自动推塔
    xianyu.task_auto_tower()
    # # 自动答题
    # xianyu.task_auto_answer()
    xianyu.task_auto_fish()
