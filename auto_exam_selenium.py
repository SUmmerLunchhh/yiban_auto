import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==================== 配置区域 ====================
API_KEY = "【在此处用APIkey替换这段内容】"
API_URL = "https://api.deepseek.com/chat/completions"
EXAM_URL = "【在此处用考试界面URL替换这段内容】"
RULES_FILE = "rules.txt"
# ==================================================


def get_current_question_type(driver):
  """精准判断当前题型"""
  try:
    q_type = driver.execute_script("""
            let headers = Array.from(document.querySelectorAll('h2, h3, .panel-title, .title, div')).filter(el => 
                el.innerText.includes('单选') || el.innerText.includes('多选') || el.innerText.includes('判断')
            );
            if (headers.length === 0) return '单选';
            let lastHeader = headers[headers.length - 1].innerText;
            if (lastHeader.includes('多选')) return '多选';
            if (lastHeader.includes('判断')) return '判断';
            return '单选';
        """)
    return q_type
  except:
    return "单选"


def get_question_and_options_detail(driver):
  """不仅抓题目，还要把当前题目下的所有选项文本（A, B, C, D...）完整抓出来"""
  try:
    data = driver.execute_script("""
            // 获取题目文本
            let qElem = document.querySelector('h3.mb, h3');
            let qText = qElem ? qElem.innerText : '';
            
            // 获取所有选项
            let optionElements = Array.from(document.querySelectorAll('div, label, span')).filter(el => {
                let t = el.innerText.trim();
                return /^[A-F][\.、]/i.test(t) || /^[A-F]$/i.test(t);
            });
            
            let optionsMap = {};
            // 把页面上所有带有 A. B. C. D. 的文本块提取出来
            let allDivs = Array.from(document.querySelectorAll('div')).map(el => el.innerText.trim());
            let validOptions = [];
            
            ['A', 'B', 'C', 'D', 'E', 'F'].forEach(letter => {
                let foundText = allDivs.find(text => text.startsWith(letter + '.') || text.startsWith(letter + '、') || text === letter);
                if (foundText) {
                    validOptions.push(foundText);
                }
            });
            
            return {
                'question': qText,
                'options': validOptions
            };
        """)
    return data["question"], data["options"]
  except Exception as e:
    print(f"抓取题目和选项出错: {e}")
    return "获取失败", ["A", "B", "C", "D"]


def search_local_rules(question_text):
  """从 rules.txt 中精准检索相关条款"""
  try:
    with open(RULES_FILE, "r", encoding="utf-8") as f:
      content = f.read()

    keywords = [
        word
        for word in question_text
        if word.strip() and word not in "，。？！（）《》“”:?-"
    ]
    paragraphs = content.split("\n")
    scored_paragraphs = []

    for p in paragraphs:
      if len(p.strip()) < 5:
        continue
      score = sum(1 for kw in keywords if kw in p)
      if score > 0:
        scored_paragraphs.append((score, p))

    scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
    best_matches = [p[1] for p in scored_paragraphs[:3]]

    return (
        "\n".join(best_matches)
        if best_matches
        else "未找到直接相关的法规条文，请根据常识与选项综合判断。"
    )
  except Exception as e:
    return "无本地开卷资料。"


def ask_ai_with_full_context(question_text, options_list, q_type):
  """将【题目 + 完整选项文字 + 开卷原文】一起打包发给 AI"""
  try:
    matched_rules = search_local_rules(question_text)
    options_text_block = "\n".join(options_list)
    valid_letters = [opt[0].upper() for opt in options_list if opt]
    if not valid_letters:
      valid_letters = ["A", "B", "C", "D"]

    print(f"题目: {question_text}")
    print(f"完整选项: {options_list}")

    if "多选" in q_type:
      rule_desc = (
          "这是一道【多选题】。\n"
          f"合法选项范围：{valid_letters}。\n"
          "请结合开卷原文与各个选项的文字说明，选出所有正确的选项，用英文逗号隔开（例如 A,B）。"
      )
    elif "判断" in q_type:
      rule_desc = (
          "这是一道【判断题】。正确返回 A，错误返回 B。绝对不能输出数字！"
      )
    else:
      rule_desc = (
          "这是一道【单选题】。请在上述选项中选择【一个】最正确的字母（如 A、B、C、D），绝对不准返回多个字母或数字！"
      )

    system_prompt = (
        "你是一个精通高校校规的开卷考试满分学生。\n"
        f"当前题型：【{q_type}】\n"
        f"{rule_desc}\n\n"
        f"【本地开卷参考法规原文】：\n{matched_rules}\n\n"
        "【铁律】\n"
        "1. 必须仔细比对下方提供的各个【选项文字】和【开卷原文】进行答题，绝不准无脑选 A！\n"
        "2. 严禁输出任何汉字、数字、标点（逗号除外）或解释说明。\n"
        "3. 只能输出纯字母或英文逗号隔开的字母组合。"
    )

    user_prompt = (
        f"题目内容：\n{question_text}\n\n各选项具体内容：\n{options_text_block}"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }

    response = requests.post(
        API_URL, headers=headers, data=json.dumps(payload), timeout=30
    )
    result = response.json()
    
    ans = result["choices"][0]["message"]["content"].strip()
    print(f"AI 最终给出的答案: {ans}")
    return ans, valid_letters

  except Exception as e:
    print(f"❌ 发生报错: {e}")
    return "A", ["A", "B", "C", "D"]


def main():
  print("正在启动浏览器...")
  driver = webdriver.Chrome(
      service=Service(ChromeDriverManager().install())
  )
  driver.get(EXAM_URL)

  print("=" * 50)
  print("【操作指南】")
  print("1. 确保同目录下已建好 rules.txt 且填入相关校规；")
  print("2. 登录易班并进入考试页面；")
  print("3. 回到黑窗口按回车开始！")
  print("=" * 50)
  input(">>> 请在完成登录后，按回车键（Enter）开始全自动开卷答题...")

  print("开始全自动答题循环...")
  time.sleep(2)

  question_index = 1
  while True:
    try:
      # 获取题型
      q_type = get_current_question_type(driver)
      
      # 抓取题目和完整选项内容
      q_text, options_list = get_question_and_options_detail(driver)
      
      if not q_text or q_text == "获取失败":
        print("未检测到有效题目，可能考试已结束。")
        break

      print(f"\n----------------------------------")
      print(f"正在处理第 {question_index} 题 | 题型: {q_type}")

      # 让 AI 带着题目、选项文字、开卷原文一块儿做题
      ai_ans, valid_options = ask_ai_with_full_context(
          q_text, options_list, q_type
      )

      # 清洗答案
      raw_answers = [
          ans.strip().upper()
          for ans in ai_ans.replace("，", ",").replace(" ", "").split(",")
          if ans.strip()
      ]
      if len(raw_answers) == 1 and len(raw_answers[0]) > 1:
        raw_answers = list(raw_answers[0])

      answers = [char for char in raw_answers if char in valid_options]
      print(f"最终勾选选项: {answers}")

      # 依次勾选
      for ans_letter in answers:
        try:
          option_xpath = (
              f"//div[contains(text(), '{ans_letter}.') or"
              f" starts-with(text(), '{ans_letter}')]"
          )
          target_option = driver.find_element(By.XPATH, option_xpath)
          target_option.click()
          time.sleep(0.3)
        except Exception as ex:
          print(f"自动勾选选项 {ans_letter} 失败: {ex}")

      time.sleep(0.5)

      # 下一题
      try:
        next_btn = driver.find_element(
            By.XPATH,
            "//button[contains(text(), '下一题') or contains(text(),'保存') or"
            " contains(text(),'次题')]",
        )
        next_btn.click()
        question_index += 1
        time.sleep(1)
      except:
        print("未找到‘下一题’按钮，可能已经到达最后一题。")
        break

    except Exception as e:
      print(f"未检测到题目元素或答题结束: {e}")
      break

  print("\n循环结束！请检查无误后自行点击提交。")
  input("\n任务执行完毕。按回车键关闭浏览器...")
  driver.quit()


if __name__ == "__main__":
  main()