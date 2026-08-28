# -*- coding: utf-8 -*-
"""批量创建飞书路演 PPT 页面"""
import json
import subprocess
import sys
import textwrap

PRESENTATION_ID = "AkudsICP6luMiSdRc75ceAzpnqf"

# 颜色定义
NAVY = "rgb(26,54,93)"          # #1a365d
NAVY2 = "rgb(30,60,114)"        # 深蓝
BLUE = "rgb(59,130,246)"        # 科技蓝
GREEN = "rgb(56,161,105)"       # 医疗绿 #38a169
ORANGE = "rgb(221,107,32)"      # 橙色 #dd6b20
RED = "rgb(229,62,62)"          # 红色 #e53e3e
PURPLE = "rgb(128,90,213)"      # 紫色 #805ad5
GRAY = "rgb(113,128,150)"       # 灰色 #718096
DARK = "rgb(45,55,72)"          # 深灰 #2d3748
LIGHT_BG = "rgb(247,250,252)"   # 浅灰背景 #f7fafc
WHITE = "rgb(255,255,255)"

# 渐变背景（深色科技风）
GRADIENT_DARK = "linear-gradient(135deg,rgba(26,54,93,1) 0%,rgba(15,23,42,1) 100%)"
GRADIENT_BLUE = "linear-gradient(135deg,rgba(30,60,114,1) 0%,rgba(59,130,246,1) 100%)"


def esc(s: str) -> str:
    """XML 文本转义"""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def shape_text(x, y, w, h, text, text_type="body", align="left", color=WHITE, bold=False, font_size=None):
    attrs = f'textType="{text_type}" textAlign="{align}" color="{color}"'
    if bold:
        attrs += ' bold="true"'
    if font_size:
        attrs += f' fontSize="{font_size}"'
    return f'''<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">
  <content {attrs}>
    <p>{esc(text)}</p>
  </content>
</shape>'''


def shape_rect(x, y, w, h, fill_color, radius=0, border=None):
    r_attr = f' radius="{radius}"' if radius else ''
    border_xml = f'\n  <border color="{border}" width="1"/>' if border else ''
    return f'''<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}"{r_attr}>
  <fill>
    <fillColor color="{fill_color}"/>
  </fill>{border_xml}
</shape>'''


def shape_icon(x, y, size, icon_type, color=None):
    # 使用简单的圆形+字母作为图标占位，因为 iconpark 路径不确定
    circle = shape_rect(x, y, size, size, color or BLUE, radius=size // 2)
    return circle


def slide_wrap(content_xml, bg_color=None, note=None):
    bg = f'''<style>
    <fill>
      <fillColor color="{bg_color}"/>
    </fill>
  </style>''' if bg_color else ""
    note_xml = f'''<note>
    <content textType="body">
      <p>{esc(note)}</p>
    </content>
  </note>''' if note else ""
    return f'''<slide xmlns="http://www.larkoffice.com/sml/2.0">
  {bg}
  <data>
    {content_xml}
  </data>
  {note_xml}
</slide>'''


def create_slide(content_xml, bg=None, note=None):
    return slide_wrap(content_xml, bg, note)


# ===================== 页面定义 =====================
def slide_1():
    """封面"""
    # 标题
    title = shape_text(80, 160, 800, 80, "医保智脑", "title", "center", WHITE, True, 64)
    subtitle = shape_text(80, 250, 800, 50, "基于可信数据空间的个人医保智能体", "sub-headline", "center", WHITE, False, 28)
    team = shape_text(80, 330, 800, 40, "全球脑机接口×医保创新场景大赛 · 场景应用赛道", "body", "center", "rgb(160,174,192)", False, 18)
    date = shape_text(80, 380, 800, 30, "2026年6月", "caption", "center", "rgb(160,174,192)", False, 16)
    # 底部装饰条
    bar = shape_rect(0, 500, 960, 40, BLUE)
    content = "\n".join([title, subtitle, team, date, bar])
    return create_slide(content, GRADIENT_DARK, "各位评委、各位老师，大家好。今天我为大家带来我们的项目——医保智脑·脑电健康卫士。")


def slide_2():
    """痛点场景"""
    title = shape_text(80, 50, 800, 50, "张阿姨的困境", "headline", "left", DARK, True, 40)
    sub = shape_text(80, 100, 800, 30, "58岁，退休工人，交了这么多年医保，用的时候却什么都看不懂", "body", "left", GRAY, False, 18)
    # 左侧大卡片
    card = shape_rect(80, 160, 400, 300, WHITE, radius=12, border="rgb(226,232,240)")
    icon1 = shape_rect(110, 190, 48, 48, ORANGE, radius=24)
    t1 = shape_text(170, 190, 280, 48, "排队3小时", "sub-headline", "left", DARK, True, 24)
    p1 = shape_text(110, 250, 340, 60, "只为问一句：我这个能报多少？", "body", "left", DARK, False, 18)
    icon2 = shape_rect(110, 330, 48, 48, RED, radius=24)
    t2 = shape_text(170, 330, 280, 48, "看不懂政策", "sub-headline", "left", DARK, True, 24)
    p2 = shape_text(110, 390, 340, 50, "起付线、自付比例、乙类药…全是术语", "body", "left", DARK, False, 18)
    # 右侧数据
    rcard = shape_rect(520, 160, 360, 300, NAVY, radius=12)
    rt1 = shape_text(550, 200, 300, 60, "每年多花", "body", "left", WHITE, False, 20)
    rt2 = shape_text(550, 250, 300, 80, "上千元", "title", "left", ORANGE, True, 48)
    rt3 = shape_text(550, 340, 300, 80, "错过政策红利，不知道能享什么待遇", "body", "left", WHITE, False, 18)
    content = "\n".join([title, sub, card, icon1, t1, p1, icon2, t2, p2, rcard, rt1, rt2, rt3])
    return create_slide(content, LIGHT_BG, "张阿姨，58岁，退休工人。昨天刚看完门诊，今天一早就赶到医保大厅，排了3个小时，只问了一句话——'我这个能报多少？'这不是个案，这是5600万参保人每天都在经历的困境。")


def slide_3():
    """三组数据"""
    title = shape_text(80, 50, 800, 50, "5600万人的信息鸿沟", "headline", "left", DARK, True, 40)
    # 三个卡片
    cards = []
    xs = [80, 340, 600]
    numbers = ["2.5亿次", "47分钟", "80%"]
    labels = ["5600万参保人\n人均每年咨询3.2次", "一份医保政策文件\n平均阅读时长", "参保人不知道\n自己可享受哪些红利"]
    icons = ["🔢", "📄", "💰"]
    colors = [BLUE, ORANGE, RED]
    for i in range(3):
        x = xs[i]
        c = shape_rect(x, 140, 240, 300, WHITE, radius=12, border="rgb(226,232,240)")
        ic = shape_rect(x + 96, 170, 48, 48, colors[i], radius=24)
        num = shape_text(x + 20, 240, 200, 60, numbers[i], "title", "center", colors[i], True, 36)
        lab = shape_text(x + 20, 320, 200, 80, labels[i], "body", "center", DARK, False, 16)
        cards.extend([c, ic, num, lab])
    bottom = shape_text(80, 480, 800, 40, "本质：信息不对称 —— 政策在文件里，权益在系统里，参保人和它们之间隔着一堵墙", "body", "center", DARK, True, 20)
    content = "\n".join([title] + cards + [bottom])
    return create_slide(content, LIGHT_BG, "三组数据：每年2.5亿次咨询需求，供需严重失衡；政策文件47分钟才能读完，普通人看不懂；80%的参保人不知道自己能享受什么。本质是信息不对称。")


def slide_4():
    """方案亮相"""
    title = shape_text(80, 60, 800, 60, "医保智脑", "title", "center", WHITE, True, 56)
    subtitle = shape_text(80, 130, 800, 40, "让每个参保人拥有一个懂医保、懂健康、懂政策的 AI 管家", "sub-headline", "center", "rgb(203,213,224)", False, 24)
    # 三大能力
    abilities = [
        ("听懂你说什么", "自然语言交互", BLUE),
        ("看懂你拿什么", "OCR 票据识别", GREEN),
        ("主动关心你", "健康风险预警", ORANGE),
    ]
    items = []
    xs = [120, 360, 600]
    for i, (t, d, color) in enumerate(abilities):
        x = xs[i]
        c = shape_rect(x, 220, 220, 180, "rgba(255,255,255,0.1)", radius=12, border="rgba(255,255,255,0.2)")
        tt = shape_text(x + 20, 250, 180, 40, t, "sub-headline", "center", WHITE, True, 20)
        dd = shape_text(x + 20, 310, 180, 60, d, "body", "center", "rgb(203,213,224)", False, 16)
        items.extend([c, tt, dd])
    slogan = shape_text(80, 450, 800, 50, "懂医保 · 懂健康 · 懂政策", "headline", "center", WHITE, True, 32)
    content = "\n".join([title, subtitle] + items + [slogan])
    return create_slide(content, GRADIENT_BLUE, "所以我们做了医保智脑——让每个参保人拥有一个懂医保、懂健康、懂政策的AI管家。它不只是被动回答，它能听懂你、看懂你、主动关心你。")


def slide_5():
    """多智能体架构"""
    title = shape_text(80, 40, 800, 50, "五大智能体 · 协同作战", "headline", "left", DARK, True, 40)
    sub = shape_text(80, 90, 800, 30, "编排器自动识别意图，路由到最合适的专业智能体", "body", "left", GRAY, False, 18)
    # 中心编排器
    center = shape_rect(400, 210, 160, 160, NAVY, radius=80)
    ct = shape_text(400, 270, 160, 40, "编排器", "sub-headline", "center", WHITE, True, 22)
    # 五个智能体
    agents = [
        ("权益管家", "医保权益\n查询测算", BLUE, 80, 80),
        ("报销助手", "OCR票据\n报销预审", GREEN, 720, 80),
        ("健康卫士", "健康画像\n风险预警", ORANGE, 80, 360),
        ("政策参谋", "政策匹配\n省钱计算", PURPLE, 720, 360),
        ("安全守门", "数据授权\n合规审计", GRAY, 400, 430),
    ]
    items = [center, ct]
    for name, desc, color, x, y in agents:
        items.append(shape_rect(x, y, 140, 100, WHITE, radius=12, border="rgb(226,232,240)"))
        items.append(shape_text(x + 10, y + 15, 120, 30, name, "body", "center", color, True, 16))
        items.append(shape_text(x + 10, y + 50, 120, 40, desc, "caption", "center", DARK, False, 13))
    content = "\n".join([title, sub] + items)
    return create_slide(content, LIGHT_BG, "底层是5个专业智能体加1个编排器。用户说一句话，编排器自动识别意图，路由到最合适的智能体，甚至可以多智能体协同。其中健康卫士是我们的核心创新。")


def slide_6():
    """Demo 1 权益查询"""
    title = shape_text(80, 40, 800, 50, "Demo 1 · 权益查询", "headline", "left", DARK, True, 40)
    # 左侧输入框
    input_box = shape_rect(80, 120, 420, 80, "rgb(235,248,255)", radius=12)
    input_text = shape_text(100, 140, 380, 40, "帮我看看我的医保情况", "body", "left", DARK, False, 18)
    # 右侧 dashboard
    dash = shape_rect(540, 120, 340, 360, WHITE, radius=12, border="rgb(226,232,240)")
    items = [
        ("参保类型", "城镇职工基本医疗保险", BLUE),
        ("个人账户余额", "¥3,286.50", GREEN),
        ("缴费年限", "23 / 25 年", ORANGE),
        ("门诊报销比例", "社区55%  三级50%", BLUE),
        ("住院报销比例", "一级95%  三级85%", BLUE),
    ]
    y = 150
    items_xml = []
    for label, value, color in items:
        items_xml.append(shape_text(570, y, 140, 25, label, "caption", "left", GRAY, False, 14))
        items_xml.append(shape_text(570, y + 25, 280, 30, value, "body", "left", DARK, True, 18))
        y += 55
    # 温馨提示
    tip = shape_rect(80, 230, 420, 120, "rgb(254,252,232)", radius=12, border="rgb(252,211,77)")
    tip_t = shape_text(100, 250, 380, 30, "⚠️ 温馨提示", "body", "left", ORANGE, True, 18)
    tip_c = shape_text(100, 285, 380, 50, "缴费年限还差2年即可达终身医保条件，请保持连续缴费", "body", "left", DARK, False, 16)
    content = "\n".join([title, input_box, input_text, dash] + items_xml + [tip, tip_t, tip_c])
    return create_slide(content, LIGHT_BG, "张阿姨说'帮我看看我的医保情况'，一句话，所有关键信息一目了然。而且它还主动提醒了缴费年限——这种'多想一步'的能力，传统系统做不到。")


def slide_7():
    """Demo 2 报销预审"""
    title = shape_text(80, 40, 800, 50, "Demo 2 · 报销预审", "headline", "left", DARK, True, 40)
    # 左侧票据识别
    card1 = shape_rect(80, 120, 420, 180, WHITE, radius=12, border="rgb(226,232,240)")
    c1t = shape_text(100, 140, 380, 30, "📄 票据识别", "body", "left", DARK, True, 18)
    c1d = shape_text(100, 175, 380, 100, "某区社区卫生服务中心\n2026-06-10  |  2型糖尿病\n费用总额：¥486.30", "body", "left", DARK, False, 16)
    # 右侧计算
    card2 = shape_rect(540, 120, 340, 180, WHITE, radius=12, border="rgb(226,232,240)")
    c2t = shape_text(560, 140, 300, 30, "🧮 报销预审", "body", "left", DARK, True, 18)
    calc_lines = [
        "费用总额：¥486.30",
        "乙类先自付：-¥12.48",
        "可报销金额：¥473.82",
        "未达起付线，本次报销：¥0",
    ]
    y = 175
    calc_xml = []
    for line in calc_lines:
        calc_xml.append(shape_text(560, y, 300, 22, line, "body", "left", DARK, False, 15))
        y += 25
    # 底部提醒
    tip = shape_rect(80, 330, 800, 160, "rgb(254,226,226)", radius=12, border="rgb(252,129,129)")
    tip_t = shape_text(100, 350, 760, 30, "💡 智能提醒", "body", "left", RED, True, 18)
    tip_c = shape_text(100, 390, 760, 80, "您可能符合门诊慢病待遇申请条件。申请后起付线降至200元，报销比例提高至75%。\n不只是告诉你'报不了'，而是告诉你'怎么才能报得了'。", "body", "left", DARK, False, 16)
    content = "\n".join([title, card1, c1t, c1d, card2, c2t] + calc_xml + [tip, tip_t, tip_c])
    return create_slide(content, LIGHT_BG, "上传一张票据，OCR自动识别，报销计算逐步展示。关键是最后这条提醒——不只是告诉你'报不了'，而是告诉你'怎么才能报得了'。")


def slide_8():
    """Demo 3 健康预警"""
    title = shape_text(80, 40, 800, 50, "Demo 3 · 健康预警 — 从被动报销到主动预防", "headline", "left", DARK, True, 36)
    # 左侧预警卡片
    warn = shape_rect(80, 120, 400, 320, WHITE, radius=12, border=RED)
    w_t = shape_text(100, 140, 360, 40, "🔴 健康预警", "sub-headline", "left", RED, True, 24)
    w_c = shape_text(100, 190, 360, 80, "连续3个月购买降糖药物，未复查糖化血红蛋白", "body", "left", DARK, False, 18)
    w_s = shape_text(100, 280, 360, 50, "糖尿病管理评分", "body", "left", GRAY, False, 16)
    w_n = shape_text(100, 320, 360, 80, "58分", "title", "left", ORANGE, True, 56)
    w_d = shape_text(180, 350, 200, 30, "较上季度 ↓12分", "body", "left", RED, False, 16)
    # 右侧雷达图用文字表示
    radar = shape_rect(520, 120, 360, 320, NAVY, radius=12)
    r_t = shape_text(540, 140, 320, 30, "五维健康画像", "body", "left", WHITE, True, 18)
    dims = [
        ("慢病管理", "58分", ORANGE),
        ("用药规范", "72分", BLUE),
        ("就医频率", "65分", BLUE),
        ("健康指标", "50分", RED),
        ("生活方式", "68分", BLUE),
    ]
    y = 185
    radar_xml = []
    for label, score, color in dims:
        radar_xml.append(shape_text(540, y, 140, 22, label, "body", "left", "rgb(203,213,224)", False, 15))
        radar_xml.append(shape_text(700, y, 120, 22, score, "body", "left", color, True, 15))
        y += 32
    # 建议
    sug = shape_text(540, 370, 320, 50, "改善建议：复查 · 饮食调整 · 申请慢病待遇", "caption", "left", WHITE, False, 14)
    content = "\n".join([title, warn, w_t, w_c, w_s, w_n, w_d, radar, r_t] + radar_xml + [sug])
    return create_slide(content, LIGHT_BG, "这是最核心的功能——医保智脑不只是被动回答问题，它会主动关心你。检测到张阿姨3个月连续买降糖药但没复查，主动推送预警。从'事后报销'到'事前预防'，这是范式转变。")


def slide_9():
    """Demo 4 政策匹配"""
    title = shape_text(80, 40, 800, 50, "Demo 4 · 政策精准匹配", "headline", "left", DARK, True, 40)
    sub = shape_text(80, 90, 800, 30, "输入：我有什么政策可以享受？", "body", "left", GRAY, False, 18)
    # 三个政策卡片
    cards = []
    policies = [
        ("⭐ 门诊慢病待遇", "年省 ¥2,016", "最推荐", GREEN),
        ("大病保险", "年度超1.5万自动触发", "自动", BLUE),
        ("个人账户家庭共济", "余额可给亲属使用", "便民", PURPLE),
    ]
    y = 140
    for name, saving, tag, color in policies:
        c = shape_rect(80, y, 560, 100, WHITE, radius=12, border="rgb(226,232,240)")
        n = shape_text(110, y + 20, 300, 30, name, "body", "left", DARK, True, 18)
        s = shape_text(110, y + 55, 300, 30, saving, "body", "left", color, True, 18)
        t = shape_rect(500, y + 30, 100, 40, color, radius=20)
        tt = shape_text(500, y + 35, 100, 30, tag, "caption", "center", WHITE, True, 14)
        cards.extend([c, n, s, t, tt])
        y += 120
    # 右侧汇总
    total = shape_rect(680, 140, 200, 340, GREEN, radius=12)
    total_t = shape_text(700, 200, 160, 40, "年度可节省", "body", "center", WHITE, False, 18)
    total_n = shape_text(700, 260, 160, 80, "¥2,016", "title", "center", WHITE, True, 42)
    total_d = shape_text(700, 360, 160, 80, "让政策红利\n从看得见\n到拿得到", "body", "center", WHITE, False, 16)
    content = "\n".join([title, sub] + cards + [total, total_t, total_n, total_d])
    return create_slide(content, LIGHT_BG, "张阿姨不知道自己可以享受门诊慢病待遇。医保智脑帮她匹配到3项政策，最推荐的一项每年能省2016元。让政策红利从'看得见摸不着'变成'看得见拿得到'。")


def slide_10():
    """四大技术创新"""
    title = shape_text(80, 40, 800, 50, "四大技术创新", "headline", "center", DARK, True, 40)
    innovations = [
        ("Multi-Agent\n多智能体架构", "5个专业智能体\n+1个编排器\n支持三种协作模式", BLUE),
        ("可信数据空间\n对齐", "对接浙江省\n1+3+N框架\n可用不可见", GREEN),
        ("健康预警\n创新", "从事后报销\n到事前预防\n五维健康画像", ORANGE),
        ("全链路\n可解释性", "报销有公式\n政策有原文\n预警有证据", PURPLE),
    ]
    items = []
    positions = [(80, 120), (520, 120), (80, 320), (520, 320)]
    for (t, d, color), (x, y) in zip(innovations, positions):
        c = shape_rect(x, y, 360, 170, WHITE, radius=12, border="rgb(226,232,240)")
        bar = shape_rect(x, y, 8, 170, color, radius=4)
        tt = shape_text(x + 25, y + 20, 310, 50, t, "sub-headline", "left", DARK, True, 20)
        dd = shape_text(x + 25, y + 80, 310, 70, d, "body", "left", DARK, False, 15)
        items.extend([c, bar, tt, dd])
    bottom = shape_text(80, 510, 800, 30, "不做黑箱 AI，做参保人能看懂、能信任的 AI", "body", "center", DARK, True, 18)
    content = "\n".join([title] + items + [bottom])
    return create_slide(content, LIGHT_BG, "四大技术创新：多智能体架构实现专业分工和智能调度；可信数据空间对齐确保安全合规；健康预警实现从被动到主动的范式转变；全链路可解释让每个决策都有据可查。")


def slide_11():
    """可信数据空间"""
    title = shape_text(80, 40, 800, 50, "站在省级战略的肩膀上", "headline", "left", DARK, True, 40)
    # 时间轴
    timeline = shape_rect(80, 110, 800, 80, WHITE, radius=12, border="rgb(226,232,240)")
    t1 = shape_text(100, 130, 220, 40, "2024.12\n国家医保局签约", "body", "left", DARK, False, 14)
    t2 = shape_text(360, 130, 220, 40, "2025.5.29\n浙江发布可信数据空间", "body", "left", DARK, False, 14)
    t3 = shape_text(620, 130, 220, 40, "现在\n全国重点示范场景", "body", "left", DARK, False, 14)
    # 1+3+N 架构
    arch = shape_rect(80, 220, 800, 250, NAVY, radius=12)
    a_t = shape_text(100, 240, 760, 40, "浙江省医保行业可信数据空间 · 1+3+N 架构", "sub-headline", "left", WHITE, True, 24)
    # 底座
    base = shape_rect(100, 300, 740, 50, BLUE, radius=8)
    base_t = shape_text(100, 315, 740, 20, "1 个数据底座：统一数据治理平台", "body", "center", WHITE, True, 18)
    # 能力
    caps = [
        ("隐私计算", "可用不可见"),
        ("区块链存证", "可信可追溯"),
        ("数据沙箱", "可控可计量"),
    ]
    cx = [100, 330, 560]
    caps_xml = []
    for i, (name, desc) in enumerate(caps):
        c = shape_rect(cx[i], 370, 200, 70, "rgba(255,255,255,0.15)", radius=8)
        n = shape_text(cx[i], 385, 200, 25, name, "body", "center", WHITE, True, 16)
        d = shape_text(cx[i], 415, 200, 20, desc, "caption", "center", "rgb(203,213,224)", False, 13)
        caps_xml.extend([c, n, d])
    apps = shape_text(100, 470, 740, 30, "N 个应用场景  →  医保智脑 = 可信数据空间在个人服务端的落地", "body", "left", WHITE, False, 16)
    content = "\n".join([title, timeline, t1, t2, t3, arch, a_t, base, base_t] + caps_xml + [apps])
    return create_slide(content, LIGHT_BG, "我们的架构完全对齐浙江省医保数据要素战略的「1+3+N」框架。隐私计算、区块链存证、数据沙箱三大能力，确保数据可用不可见、可控可计量、可信可追溯。")


def slide_12():
    """社会价值"""
    title = shape_text(80, 40, 800, 50, "从被动报销到主动健康", "headline", "center", DARK, True, 40)
    # 三个大字
    bigs = [
        ("5600万", "参保人"),
        ("5600万次", "每年少跑腿"),
        ("数十亿", "政策红利释放"),
    ]
    xs = [80, 360, 640]
    bigs_xml = []
    for i, (num, label) in enumerate(bigs):
        c = shape_rect(xs[i], 120, 240, 160, WHITE, radius=12, border="rgb(226,232,240)")
        n = shape_text(xs[i], 150, 240, 70, num, "title", "center", BLUE, True, 38)
        l = shape_text(xs[i], 230, 240, 30, label, "body", "center", DARK, False, 16)
        bigs_xml.extend([c, n, l])
    # 范式对比
    old = shape_rect(80, 310, 420, 100, "rgb(237,242,247)", radius=12)
    old_t = shape_text(100, 330, 380, 30, "旧范式：人 → 排队 → 窗口 → 报销", "body", "left", GRAY, False, 18)
    new = shape_rect(80, 430, 420, 80, GREEN, radius=12)
    new_t = shape_text(100, 450, 380, 40, "新范式：人 → 手机 → 智脑 → 预防+报销", "body", "left", WHITE, True, 18)
    # 右侧金句
    quote = shape_text(540, 330, 340, 160, "少花1块钱医疗费\n比报销1块钱\n更有价值", "sub-headline", "left", DARK, True, 24)
    content = "\n".join([title] + bigs_xml + [old, old_t, new, new_t, quote])
    return create_slide(content, LIGHT_BG, "医保智脑推动的是范式转变——从被动报销到主动健康。少花1块钱医疗费比报销1块钱更有价值。5600万参保人，每人省一次跑腿，多享一项政策，社会效益不可估量。")


def slide_13():
    """商业模式"""
    title = shape_text(80, 40, 800, 50, "三层商业模式", "headline", "center", DARK, True, 40)
    # 金字塔
    levels = [
        ("To G 政府", "智能客服替代人工窗口\n基金智能监管\n降低30%-50%重复咨询", "rgb(59,130,246)", 80, 360, 800),
        ("To B 商保/药企", "数据赋能：精准定价、快速理赔\n真实世界数据分析", "rgb(56,161,105)", 180, 260, 600),
        ("To C 个人", "基础权益查询：免费\n健康管理增值服务：付费", "rgb(221,107,32)", 280, 160, 400),
    ]
    levels_xml = []
    for name, desc, color, x, y, w in levels:
        c = shape_rect(x, y, w, 90, color, radius=12)
        n = shape_text(x + 20, y + 20, w - 40, 30, name, "sub-headline", "left", WHITE, True, 22)
        d = shape_text(x + 20, y + 55, w - 40, 30, desc, "body", "left", WHITE, False, 14)
        levels_xml.extend([c, n, d])
    content = "\n".join([title] + levels_xml)
    return create_slide(content, LIGHT_BG, "三层商业模式：To G提供智能客服降低经办成本；To B基于可信数据空间提供数据赋能；To C基础免费、增值付费。从医保管家升级为健康管家。")


def slide_14():
    """落地路线图"""
    title = shape_text(80, 40, 800, 50, "从黑客松到全省推广", "headline", "center", DARK, True, 40)
    # 时间轴
    line = shape_rect(80, 180, 800, 6, "rgb(226,232,240)", radius=3)
    phases = [
        ("Phase 1\n1-3个月", "沙箱验证\n接入数据赋能实验室\n脱敏数据验证", BLUE),
        ("Phase 2\n3-6个月", "区县试点\n1-2个区县\n覆盖5-10万人", GREEN),
        ("Phase 3\n6-12个月", "全省推广\n规模化部署\n依托可信数据空间", ORANGE),
    ]
    xs = [120, 400, 680]
    phases_xml = [line]
    for i, (title_text, desc, color) in enumerate(phases):
        x = xs[i]
        dot = shape_rect(x + 60, 165, 30, 30, color, radius=15)
        c = shape_rect(x, 230, 200, 200, WHITE, radius=12, border="rgb(226,232,240)")
        t = shape_text(x + 15, 250, 170, 50, title_text, "sub-headline", "center", color, True, 18)
        d = shape_text(x + 15, 310, 170, 90, desc, "body", "center", DARK, False, 14)
        phases_xml.extend([dot, c, t, d])
    here = shape_text(100, 470, 200, 40, "👆 我们在这里", "body", "left", ORANGE, True, 18)
    content = "\n".join([title] + phases_xml + [here])
    return create_slide(content, LIGHT_BG, "落地分三步：先在数据赋能实验室用脱敏数据验证，再选1-2个区县试点5-10万人，最后全省推广。关键是我们有可信数据空间的基础设施支撑。")


def slide_15():
    """团队"""
    title = shape_text(80, 40, 800, 50, "团队", "headline", "center", DARK, True, 40)
    role1 = shape_text(80, 120, 250, 40, "项目负责人", "sub-headline", "center", NAVY, True, 20)
    role1d = shape_text(80, 165, 250, 80, "统筹协调\n申报书统稿\n大赛对接", "body", "center", DARK, False, 14)
    role2 = shape_text(285, 120, 250, 40, "临床专家", "sub-headline", "center", BLUE, True, 20)
    role2d = shape_text(285, 165, 250, 80, "纳排标准\n量表选择\n效度验证", "body", "center", DARK, False, 14)
    role3 = shape_text(490, 120, 250, 40, "技术负责人", "sub-headline", "center", BLUE, True, 20)
    role3d = shape_text(490, 165, 250, 80, "EEG算法\n系统开发\n多智能体", "body", "center", DARK, False, 14)
    tags = "医工信交叉  |  Python/FastAPI  |  Next.js  |  EEG/BCI  |  Multi-Agent"
    tags_t = shape_text(80, 280, 800, 30, tags, "body", "center", BLUE, False, 16)
    contrib = shape_text(80, 330, 800, 30, "151项单元测试 + 68项冒烟测试全绿 · 赛道7三大核心能力完整覆盖", "body", "center", DARK, False, 16)
    bottom = shape_text(80, 400, 800, 30, "脑智同心 · 全球脑机接口×医保创新场景大赛", "body", "center", DARK, True, 18)
    content = "\n".join([title, role1, role1d, role2, role2d, role3, role3d, tags_t, contrib, bottom])
    return create_slide(content, LIGHT_BG, "我们是一支医工信交叉团队：项目负责人统筹协调，临床专家保障医学严谨性，技术负责人实现BCI×医保全链路系统。")


def slide_16():
    """结尾"""
    title = shape_text(80, 100, 800, 60, "让脑电数据守护健康", "title", "center", WHITE, True, 48)
    l2 = shape_text(80, 170, 800, 60, "让医保政策主动找到你", "title", "center", WHITE, True, 48)
    l3 = shape_text(80, 240, 800, 70, "从被动报销到主动健康", "title", "center", ORANGE, True, 52)
    slogan = shape_text(80, 350, 800, 40, "懂医保 · 懂健康 · 懂脑电", "sub-headline", "center", "rgb(203,213,224)", False, 24)
    team = shape_text(80, 430, 800, 30, "脑智同心 · 医保智脑·脑电健康卫士", "body", "center", WHITE, False, 18)
    thanks = shape_text(80, 480, 800, 40, "谢谢大家！", "headline", "center", WHITE, True, 32)
    content = "\n".join([title, l2, l3, slogan, team, thanks])
    return create_slide(content, GRADIENT_DARK, "回到张阿姨的故事。有了医保智脑，她不需要排3小时队，不需要看不懂47分钟的政策文件，不需要错过每年2016元的政策红利。让数据多跑路，让群众少跑腿，让健康早一步。谢谢大家！")


SLIDES = [
    slide_1(), slide_2(), slide_3(), slide_4(),
    slide_5(), slide_6(), slide_7(), slide_8(),
    slide_9(), slide_10(), slide_11(), slide_12(),
    slide_13(), slide_14(), slide_15(), slide_16(),
]


def create_ps1():
    lines = ["# Auto-generated by create_ppt_slides.py", r"# Run from repo root: .\scripts\create_ppt_slides_run.ps1"]
    # params 写入文件（无 BOM）
    params = json.dumps({"xml_presentation_id": PRESENTATION_ID})
    with open("scripts/ppt_params.json", "w", encoding="utf-8") as f:
        f.write(params)
    for idx, xml in enumerate(SLIDES, 1):
        payload = json.dumps({"slide": {"content": xml}})
        filename = f"scripts/ppt_payload_{idx}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(payload)
        lines.append(f"Write-Host 'Creating slide {idx}/{len(SLIDES)} ...'")
        lines.append(
            f"npx lark-cli slides xml_presentation.slide create --as user "
            f"--params @scripts/ppt_params.json "
            f"--data @scripts/ppt_payload_{idx}.json"
        )
    lines.append("Write-Host 'All slides created.'")
    with open("scripts/create_ppt_slides_run.ps1", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Generated scripts/create_ppt_slides_run.ps1")


if __name__ == "__main__":
    create_ps1()
