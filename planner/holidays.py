# planner/holidays.py
import datetime
import cnlunar  # pip install cnlunar
from lunar_python import Solar

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
    (12, 24): "平安夜",
    (12, 25): "圣诞节",
    # 可继续添加
}

# ----- 农历节日（月, 日） -----
LUNAR_HOLIDAYS = {
    (1, 1): "春节",
    (1, 15): "元宵节",
    (2, 2): "龙抬头",
    (3, 3): "上巳节",
    (5, 5): "端午节",
    (7, 7): "七夕节",
    (7, 15): "中元节",
    (8, 15): "中秋节",
    (9, 9): "重阳节",
    (10, 1): "寒衣节",
    (10, 15): "下元节",
    (12, 8): "腊八节",
    (12, 23): "北方小年",          # 北方
    (12, 24): "南方小年",          # 南方
    (12, 30): "除夕",   # 注意农历最后一天可能是29或30，cnlunar 会正确识别
}


def is_nth_weekday(date: datetime.date, nth: int, weekday: int) -> bool:
    """
    判断 date 是否是该月的第 nth 个星期 weekday（星期一=0，星期日=6）
    """
    if date.weekday() != weekday:
        return False
    # 计算这个月第一天是星期几
    first_day = date.replace(day=1)
    # 第一个 weekday 出现的日期
    first_occurrence = first_day + datetime.timedelta(days=(weekday - first_day.weekday() + 7) % 7)
    # 第 nth 个 occurrence
    target_day = first_occurrence + datetime.timedelta(weeks=nth-1)
    return date == target_day

def get_floating_events(d: datetime.date) -> list:
    events = []
    # 马丁·路德·金纪念日 (1月第三个星期一)
    # 母亲节 (5月第二个星期日)
    if d.month == 5 and is_nth_weekday(d, 2, 6):
        events.append("母亲节")
    # 父亲节 (6月第三个星期日)
    if d.month == 6 and is_nth_weekday(d, 3, 6):
        events.append("父亲节")
    # 感恩节 (11月第四个星期四)
    if d.month == 11 and is_nth_weekday(d, 4, 3):
        events.append("感恩节")

    # 复活节（需要复杂计算，可选）
    try:
        from dateutil.easter import easter
        easter_date = easter(d.year)
        if d == easter_date:
            events.append("复活节")
        # 如果需要复活节相关的周五/周一，也可以在此添加
    except ImportError:
        # 没有安装 dateutil，忽略复活节
        pass

    return events

def get_day_events(d: datetime.date) -> list:
    """返回给定日期的事件列表（节日/节气）"""
    events = []

    # 1. 公历固定节日
    md = (d.month, d.day)
    if md in SOLAR_HOLIDAYS:
        events.append(SOLAR_HOLIDAYS[md])

    # 2. 农历相关（节日和节气）
    try:
        # 正确方式：从公历日期创建 Solar，再获取农历
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()

        # 农历月日
        lunar_month = lunar.getMonth()
        lunar_day = lunar.getDay()
        lunar_md = (lunar_month, lunar_day)

        # 农历节日
        if lunar_md in LUNAR_HOLIDAYS:
            events.append(LUNAR_HOLIDAYS[lunar_md])

        # 特殊处理除夕：农历12月的最后一天
        if lunar_month == 12:
            next_day = d + datetime.timedelta(days=1)
            next_solar = Solar.fromYmd(next_day.year, next_day.month, next_day.day)
            next_lunar = next_solar.getLunar()
            if next_lunar.getMonth() != 12:
                events.append("除夕")

        # 二十四节气
        jieqi = lunar.getJieQi()
        if jieqi:
            events.append(jieqi)

    except Exception as e:
        # 调试时可打印，上线后注释
        # print(f"Lunar error for {d}: {e}")
        pass

    # 3. 浮动节日
    events.extend(get_floating_events(d))

    return events