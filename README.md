# 校园失物招领智能匹配平台

[![自动化测试](https://github.com/shylilinks/campus-lost-found/actions/workflows/ci.yml/badge.svg)](https://github.com/shylilinks/campus-lost-found/actions/workflows/ci.yml)

《软件测试与质量保证》课程原创项目。校园里东西丢了/捡到了，在平台上登记一条信息，
系统会用**文本相似度 + 类别 + 地点 + 日期新鲜度**自动算出最可能配对的记录（Top3 推荐带匹配度%），
还能开**私聊留言**窗口直接联系对方，支持**以图搜物**、**用户系统**与**消息通知**。

## 功能

- 📝 **发布登记**：丢东西 / 捡到东西都能登记，支持上传物品照片
- 🔍 **智能匹配**：TF-IDF 文本相似度(70) + 类别一致(20) + 地点重合(10) + 日期新鲜度(5)，Top3 带星级与进度条
- ✨ **同义词语义扩展**：水杯↔杯子、平板↔平板电脑、自行车↔单车……不同说法也能匹配
- ✨ **关键词高亮**：匹配页自动标绿双方描述中重合的词
- 🖼 **以图搜物**：上传照片，感知哈希（aHash）比对所有登记图片找相似物品
- 💬 **私聊留言**：每条记录一个留言窗口，2 秒自动刷新
- ✅ **状态标记**：找回/认领后标记，不再参与匹配
- 🛡 **无匹配兜底**：没匹配到时提示联系保卫处调取监控
- 🔒 **联系方式脱敏**：列表页 138****0042，详情页完整
- 👤 **用户系统**：学号注册登录，发布/留言/标记找回需登录
- 🔔 **消息通知**：新匹配、新留言自动产生通知，导航栏红点提示

## 快速开始

```bash
pip install -r requirements.txt
python app.py            # 打开 http://127.0.0.1:5000
python test_matcher.py   # 匹配算法集成测试，生成 测试报告.md
python -m pytest test_matcher_unit.py -v   # 匹配算法单元测试（pytest）
python test_e2e.py       # Web 平台端到端测试（Selenium，需本机 Chrome）
```

## 项目结构

```
├── app.py                 Flask 应用（路由 + 用户系统 + 通知 + 图片）
├── matcher.py             智能匹配算法（同义词扩展 + 四维评分）
├── hash_util.py           感知哈希 aHash 与汉明距离
├── test_matcher.py        匹配算法集成测试（10 用例）
├── test_matcher_unit.py   匹配算法 pytest 单元测试（10 用例）
├── test_e2e.py            Web 平台端到端测试（8 步全流程）
├── data/                  items.json / users.json / messages.json / notifications.json
├── templates/             页面模板（Jinja2）
├── static/style.css       样式
├── uploads/               上传的物品照片
├── demo/login.html        自带被测演示页
└── 测试报告.md            test_matcher.py 生成的测试报告
```

## 自动化测试

| 层级 | 文件 | 用例数 | 覆盖 |
| --- | --- | --- | --- |
| 单元测试 | test_matcher_unit.py | 10 | 分词过滤/同义词扩展/评分/已知配对 Top1 |
| 集成测试 | test_matcher.py | 10 | 准确率/边界/不变性/排序稳定性 |
| 端到端 | test_e2e.py | 8 | 注册→登录→发布→搜索→匹配→留言→找回→筛选 |

GitHub Actions 在每次 push 时自动运行以上全部测试（见 .github/workflows/ci.yml）。
