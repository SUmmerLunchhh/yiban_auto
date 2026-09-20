#  易班优课在线考试自动AI答题

基于 Python、Selenium 与 AI驱动的全自动开卷考试辅助脚本。能够自动抓取网页题目、比对本地开卷法规文档（RAG 检索增强），并自动完成选项勾选。

---

## 🛠️ 功能特点

1. **智能全量上下文比对**：不仅抓取题干，还会自动解析页面上的所有完整选项文本（A, B, C, D...），结合本地规则精准作答。
2. **本地法规知识库支持（RAG）**：通过关键字检索 `rules.txt` 中的校规条文，确保答案有理有据。
3. **全自动浏览器操作**：基于 Selenium 自动定位题型、填入选项并点击“下一题”。

---

## 📦 准备工作

在运行脚本前，请确保你的电脑上已经安装了：
* **Python**（建议 3.8 或以上版本）
* **Google Chrome 浏览器**

### 1. 安装依赖库
打开终端（Terminal 或 PowerShell），运行以下命令安装必要的依赖：
```bash
pip install requests selenium webdriver-manager
```
### 2. 克隆仓库到本地
```bash
git clone https://github.com/SUmmerLunchhh/yiban_auto.git
cd yiban_auto
```
### 3.将你自己的任意AI APIkey 输入yiban_auto_exam_selenium.py文件中对应替换部分，
打开网页端考试界面，将网址输入对应替换部分。（代码中【】部分）
### 4.运行代码并按提示操作。注：最后提交需自行手动提交，否则会卡在最后一题界面。
