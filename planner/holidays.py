# planner/holidays.py
import datetime
import cnlunar  # pip install cnlunar

# ----- 公历节日（固定日期） -----
SOLAR_HOLIDAYS = {
    (1, 1): "元旦",
    (2, 14): "情人节",
    (3, 8): "妇女节",
    (3, 12): "植树节",
    (4, 1): "愚人节",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (9, 10): "教师节",
    (10, 1): "国庆节",
    (10, 31): "万圣节",
    (11, 11): "光棍节",
    (12, 25): "圣诞节",
    # 可继续添加
}

# ----- 农历节日（月, 日） -----
LUNAR_HOLIDAYS = {
    (1, 1): "春节",
    (1, 15): "元宵节",
    (5, 5): "端午节",
    (7, 7): "七夕节",
    (8, 15): "中秋节",
    (9, 9): "重阳节",
    (12, 30): "除夕",  # 注意农历最后一天可能是29或30，cnlunar 会正确识别
}

def get_day_events(d: datetime.date) -> list:
    """返回给定日期的事件列表（节日/节气）"""
    events = []

    # 1. 公历节日
    md = (d.month, d.day)
    if md in SOLAR_HOLIDAYS:
        events.append(SOLAR_HOLIDAYS[md])

    # 2. 农历日期和节气（使用 cnlunar）
    try:
        # cnlunar 需要传入 datetime 对象，注意时区无关
        lunar = cnlunar.Lunar(d, godType='eight')  # godType 可选，不影响基础信息
        # 农历节日
        lunar_md = (lunar.lunarMonth, lunar.lunarDay)
        if lunar_md in LUNAR_HOLIDAYS:
            events.append(LUNAR_HOLIDAYS[lunar_md])

        # 3. 二十四节气
        if lunar.jieqi:  # jieqi 是节气名称，如 '冬至'，若无节气则为 None
            events.append(lunar.jieqi)
    except Exception as e:
        # cnlunar 可能对某些日期（如年份太早）抛出异常，这里忽略
        pass

    return events