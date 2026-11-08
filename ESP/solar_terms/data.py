"""Core metadata for the 24 solar terms.

Only fields needed by the scheduler/UI are loaded on the device.  The
long-form culture and farming text lives in culture.py and is compiled into
solar-terms.json at build time.
"""

TERMS = [
    {
        "name": '立春', "season": '春季', "angle": 315, "date_hint": '2 月 3–5 日',
        "intro": '立春是春季的第一个节气，气温开始回升，万物逐渐复苏；各地气候差异很大，农事仍要结合当地天气。',
        "available": True,
    },
    {
        "name": '雨水', "season": '春季', "angle": 330, "date_hint": '2 月 18–20 日',
        "intro": '雨水节气降水增多、气温回升，冰雪逐渐融化；实际降雨仍因地区而异。',
        "available": True,
    },
    {
        "name": '惊蛰', "season": '春季', "angle": 345, "date_hint": '3 月 5–7 日',
        "intro": '惊蛰前后春雷始鸣，蛰伏的昆虫逐渐苏醒，是春季农事开始忙碌的时段。',
        "available": True,
    },
    {
        "name": '春分', "season": '春季', "angle": 0, "date_hint": '3 月 20–22 日',
        "intro": '春分时昼夜大致平分，春季过半，气温继续回升。',
        "available": True,
    },
    {
        "name": '清明', "season": '春季', "angle": 15, "date_hint": '4 月 4–6 日',
        "intro": '清明时节天气转暖、草木萌发，民间有踏青和祭祖的习俗。',
        "available": True,
    },
    {
        "name": '谷雨', "season": '春季', "angle": 30, "date_hint": '4 月 19–21 日',
        "intro": '谷雨是春季最后一个节气，降雨对谷类作物生长很重要。',
        "available": True,
    },
    {
        "name": '立夏', "season": '夏季', "angle": 45, "date_hint": '5 月 5–7 日',
        "intro": '立夏表示夏季开始，作物进入旺盛生长期。',
        "available": True,
    },
    {
        "name": '小满', "season": '夏季', "angle": 60, "date_hint": '5 月 20–22 日',
        "intro": '小满时夏熟作物的籽粒开始饱满，但尚未完全成熟。',
        "available": True,
    },
    {
        "name": '芒种', "season": '夏季', "angle": 75, "date_hint": '6 月 5–7 日',
        "intro": '芒种是有芒作物成熟、夏种夏管繁忙的时节。',
        "available": True,
    },
    {
        "name": '夏至', "season": '夏季', "angle": 90, "date_hint": '6 月 21–22 日',
        "intro": '夏至时北半球白昼最长，此后白昼逐渐变短。',
        "available": True,
    },
    {
        "name": '小暑', "season": '夏季', "angle": 105, "date_hint": '7 月 6–8 日',
        "intro": '小暑表示天气开始炎热，但还不是一年中最热的时候。',
        "available": True,
    },
    {
        "name": '大暑', "season": '夏季', "angle": 120, "date_hint": '7 月 22–24 日',
        "intro": '大暑通常是一年中最炎热的时段，需注意高温和水分管理。',
        "available": True,
    },
    {
        "name": '立秋', "season": '秋季', "angle": 135, "date_hint": '8 月 7–9 日',
        "intro": '立秋表示秋季开始，暑气逐渐消退，但部分地区仍有高温。',
        "available": True,
    },
    {
        "name": '处暑', "season": '秋季', "angle": 150, "date_hint": '8 月 22–24 日',
        "intro": '处暑表示暑气终止，天气逐渐转凉。',
        "available": True,
    },
    {
        "name": '白露', "season": '秋季', "angle": 165, "date_hint": '9 月 7–9 日',
        "intro": '白露前后昼夜温差加大，清晨草木上可见露水。',
        "available": True,
    },
    {
        "name": '秋分', "season": '秋季', "angle": 180, "date_hint": '9 月 22–24 日',
        "intro": '秋分时昼夜大致平分，秋季过半。',
        "available": True,
    },
    {
        "name": '寒露', "season": '秋季', "angle": 195, "date_hint": '10 月 8–9 日',
        "intro": '寒露表示露水更凉、秋意加深，北方部分地区开始出现低温。',
        "available": True,
    },
    {
        "name": '霜降', "season": '秋季', "angle": 210, "date_hint": '10 月 23–24 日',
        "intro": '霜降是秋季最后一个节气，天气渐冷，昼夜温差增大。北方部分地区可能出现初霜，南方则仍可能较为温暖。',
        "available": True,
    },
    {
        "name": '立冬', "season": '冬季', "angle": 225, "date_hint": '11 月 7–8 日',
        "intro": '立冬是冬季的第一个节气，意味着冬季开始。此时气温逐渐下降，万物进入休养、蓄藏的时节。不同地区气候差异明显，农事安排应结合当地天气与作物实际情况。',
        "available": True,
    },
    {
        "name": '小雪', "season": '冬季', "angle": 240, "date_hint": '11 月 22–23 日',
        "intro": '小雪是冬季第二个节气，气温继续下降，部分地区开始出现降雪，但降雪并非各地都会发生。',
        "available": True,
    },
    {
        "name": '大雪', "season": '冬季', "angle": 255, "date_hint": '12 月 6–7 日',
        "intro": '大雪是冬季第三个节气，天气更加寒冷，降雪概率在部分地区增加，但雪量和是否降雪因地域而异。',
        "available": True,
    },
    {
        "name": '冬至', "season": '冬季', "angle": 270, "date_hint": '12 月 21–22 日',
        "intro": '冬至是二十四节气中的第二十二个节气，太阳直射点到达南回归线附近，北半球白昼最短、黑夜最长。此后白昼逐渐变长。',
        "available": True,
    },
    {
        "name": '小寒', "season": '冬季', "angle": 285, "date_hint": '1 月 5–6 日',
        "intro": '小寒是冬季第五个节气，标志着天气进入一年中较为寒冷的时段。不同地区寒冷程度和降雪情况差异较大。',
        "available": True,
    },
    {
        "name": '大寒', "season": '冬季', "angle": 300, "date_hint": '1 月 20–21 日',
        "intro": '大寒是二十四节气中的最后一个节气，通常是一年中寒冷的时段之一，也意味着新一轮节气循环即将开始。',
        "available": True,
    },
]

TERM_BY_NAME = {item["name"]: item for item in TERMS}


def all_terms():
    return TERMS


def get_term(name):
    return TERM_BY_NAME.get(name)


def term_name(index):
    return TERMS[index % 24]["name"]


def season_for_index(index):
    return TERMS[index % 24]["season"]
