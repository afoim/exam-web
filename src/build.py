import os
import glob
import json
import re

class QuizFormatError(Exception):
    """题目格式错误的自定义异常"""
    pass

class QuizBuilder:
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.quiz_template_path = os.path.join(template_dir, 'quiz_template.html')
        self.index_template_path = os.path.join(template_dir, 'index_template.html')
    
    def parse_questions(self, questions_path):
        questions = []
        current_question = None
        line_num = 0
        question_num = 0
        processed_questions = set()  # 用于统计题目编号
        
        with open(questions_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            def extract_answers(line):
                """从一行文本中提取所有括号内的答案，并返回处理后的文本"""
                answers = []
                brackets = []
                processed_text = line
                
                # 遍历所有括号，找出所有包含答案的括号
                for i, char in enumerate(line):
                    if char in '(（':
                        brackets.append((i, char))
                    elif char in ')）' and brackets:
                        start_idx, start_char = brackets.pop()
                        # 检查这对括号内的内容
                        bracket_content = line[start_idx+1:i].strip()
                        cleaned_content = bracket_content.replace(' ', '')
                        # 如果括号内容全是答案字母
                        if cleaned_content and all(c in 'ABCD' for c in cleaned_content):
                            answers.extend(list(cleaned_content))
                            # 直接替换答案为空格
                            before = processed_text[:start_idx]
                            after = processed_text[i+1:]
                            bracket_type = line[start_idx]
                            closing_bracket = ')' if bracket_type == '(' else '）'
                            processed_text = before + bracket_type + "  " + closing_bracket + after
                
                if answers:
                    return sorted(set(answers)), processed_text
                
                return None, line

            def is_question_line(line):
                """判断是否是题目行"""
                # 检查是否以数字开头（支持多个点号）
                if not any(c.isdigit() for c in line.split('.')[0].split('．')[0]):
                    return False
                # 检查是否包含括号和答案
                return ('(' in line and ')' in line) or ('（' in line and '）' in line)

            def is_option_line(line):
                """判断是否是选项行"""
                # 必须以A-D开头，后面跟着点号（支持中英文点号）
                if not line or line[0] not in 'ABCD':
                    return False
                return len(line) > 1 and (line[1] == '.' or line[1] == '．')

            def parse_options_line(line):
                """解析包含多个选项的行"""
                options = []
                # 按制表符或多个空格分割
                parts = re.split(r'\t+|\s{2,}', line)
                for part in parts:
                    part = part.strip()
                    if part and part[0] in 'ABCD':
                        # 移除选项标记（如"A．"或"A."）
                        option = re.sub(r'^[A-D][.．]', '', part).strip()
                        if option:
                            options.append(option)
                return options

            while line_num < len(lines):
                line = lines[line_num].strip()
                line_num += 1
                
                if not line:
                    continue
                
                try:
                    # 处理题目行
                    if is_question_line(line):
                        question_num += 1
                        if current_question:
                            if len(current_question['options']) != 4:
                                raise QuizFormatError(
                                    f"第{question_num-1}题（第{line_num}行之前）: 选项数量不足4个，实际只有{len(current_question['options'])}个")
                            questions.append(current_question)
                        
                        # 提取所有括号中的答案
                        answers, processed_text = extract_answers(line)
                        if not answers:
                            raise QuizFormatError(
                                f"第{question_num}题（第{line_num}行）: 无法从题目中提取出有效的答案，"
                                f"答案必须是A、B、C、D中的一个或多个")
                        
                        # 处理题目文本
                        question_text = processed_text
                        question_text = re.sub(r'^\d+\.', '', question_text).strip()  # 只移除题号
                        
                        # 初始化选项搜索行号
                        option_search_line_num = line_num
                        
                        # 在处理选项后，查找解析文本
                        explanation = ""
                        while option_search_line_num < len(lines):
                            next_line = lines[option_search_line_num].strip()
                            if next_line == "【解析】":
                                # 找到解析标记，开始收集解析文本
                                option_search_line_num += 1
                                while option_search_line_num < len(lines):
                                    next_line = lines[option_search_line_num].strip()
                                    if not next_line or is_question_line(next_line):
                                        break
                                    explanation += next_line + "\n"
                                    option_search_line_num += 1
                                break
                            elif is_question_line(next_line):
                                break
                            option_search_line_num += 1
                        
                        current_question = {
                            'question': question_text,
                            'options': [],
                            'correctAnswer': [ord(ans) - ord('A') for ans in answers],
                            'isMultipleChoice': len(answers) > 1,
                            'explanation': explanation.strip() if explanation else "暂无解析"
                        }
                        
                        # 向前查找选项
                        option_count = 0
                        option_search_line_num = line_num
                        while option_count < 4 and option_search_line_num < len(lines):
                            next_line = lines[option_search_line_num].strip()
                            if not next_line:
                                option_search_line_num += 1
                                continue
                            
                            # 如果是包含多个选项的行
                            if re.match(r'^[A-D][.．].*\s+[A-D][.．]', next_line):
                                options = parse_options_line(next_line)
                                for option in options:
                                    if option_count < 4:
                                        current_question['options'].append(option)
                                        option_count += 1
                                option_search_line_num += 1
                            # 如果是单个选项的行
                            elif is_option_line(next_line):
                                option = next_line[2:].strip()
                                if option_count < 4:
                                    current_question['options'].append(option)
                                    option_count += 1
                                option_search_line_num += 1
                            else:
                                if not is_question_line(next_line):
                                    option_search_line_num += 1
                                else:
                                    break
                        
                        if option_count < 4:
                            raise QuizFormatError(
                                f"第{question_num}题（第{line_num}行）: 选项数量不足4个，实际只有{option_count}个\n"
                                f"题目内容: {line}\n"
                                f"已找到的选项: {current_question['options']}"
                            )
                        
                        line_num = option_search_line_num  # 更新行号到最后处理的位置
                    
                except QuizFormatError as e:
                    print(f"\n格式错误: {str(e)}")
                    print(f"出错的行内容: {line}")
                    print("\n正确的格式示例:")
                    print("1.题目内容( A )。")
                    print("2.题目内容（A）。  # 中文括号也支持")
                    print("3.题目内容( A )。  # 支持多个点号")
                    print("4.多选题内容( A B D )  # 多选题示例")
                    print("A.选项1")
                    print("B.选项2")
                    print("C.选项3")
                    print("D.选项4\n")
                    raise
        
        # 验证最后一题的完整性
        if current_question:
            if len(current_question['options']) != 4:
                raise QuizFormatError(
                    f"第{question_num}题（第{line_num}行）: 选项数量不足4个，实际只有{len(current_question['options'])}个")
            questions.append(current_question)
        
        if not questions:
            raise QuizFormatError("题目文件为空或格式错误")
        
        return questions
    
    def build_questions_js(self, questions):
        def safe_json_dumps(obj):
            """自定义 JSON 序列化，保留 HTML 标签"""
            if isinstance(obj, str):
                # 进行 JSON 序列化
                json_text = json.dumps(obj, ensure_ascii=False)
                # 直接替换转义的尖括号
                return json_text.replace('\\u003c', '<').replace('\\u003e', '>')
            elif isinstance(obj, list):
                # 对列表中的每个元素进行处理
                items = [safe_json_dumps(item) if isinstance(item, str) else json.dumps(item, ensure_ascii=False) for item in obj]
                return f'[{",".join(items)}]'
            return json.dumps(obj, ensure_ascii=False)

        js_questions = []
        for i, q in enumerate(questions):
            # 直接使用处理好的题目文本，不添加序号
            question_text = q['question'].strip()
            # 在题目末尾添加题型标记
            question_text += " [" + ("多选题" if q['isMultipleChoice'] else "单选题") + "]"
            
            # 使用自定义的 JSON 序列化，确保生成有效的 JavaScript 对象
            js_questions.append(f"""{{
                question: {safe_json_dumps(question_text)},
                options: {safe_json_dumps(q['options'])},
                correctAnswer: {json.dumps(q['correctAnswer'], ensure_ascii=False)},
                isMultipleChoice: {str(q['isMultipleChoice']).lower()},
                explanation: {safe_json_dumps(q['explanation'])}
            }}""")
        
        # 生成最终的 JavaScript 代码
        js_code = "const questions = [\n    " + ",\n    ".join(js_questions) + "\n];"
        
        return js_code

    def build_quiz(self, questions_path, output_path):
        """构建单个题目页面"""
        # 读取模板
        with open(self.quiz_template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        # 解析题目
        questions = self.parse_questions(questions_path)
        
        # 生成questions.js内容
        questions_js = self.build_questions_js(questions)
        
        # 将questions_js嵌入到模板中
        html = template.replace('// QUESTIONS_PLACEHOLDER', questions_js)
        
        # 写入生成的HTML文件
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        return os.path.basename(questions_path), len(questions)

    def build_index(self, quiz_list):
        """构建导航页面"""
        # 读取模板
        with open(self.index_template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 生成题目列表HTML
        quiz_items = []
        for name, count in quiz_list:
            quiz_name = os.path.splitext(name)[0]
            quiz_items.append(
                f'<li class="quiz-item">'
                f'<a href="{quiz_name}.html" class="quiz-link">{quiz_name} ({count}题)</a>'
                f'</li>'
            )
        
        # 将题目列表嵌入到模板中
        html = template.replace('<!-- QUIZ_LIST_PLACEHOLDER -->', '\n'.join(quiz_items))
        
        # 写入生成的index.html
        with open('dist/index.html', 'w', encoding='utf-8') as f:
            f.write(html)

    def build(self):
        """构建整个项目"""
        # 确保dist目录存在
        os.makedirs('dist', exist_ok=True)
        
        # 获取所有题目文件
        quiz_list = []
        questions_dir = 'src/questions'
        for questions_path in glob.glob(os.path.join(questions_dir, '*.txt')):
            quiz_name = os.path.basename(questions_path)
            output_name = os.path.splitext(quiz_name)[0] + '.html'
            output_path = os.path.join('dist', output_name)
            
            try:
                name, count = self.build_quiz(questions_path, output_path)
                quiz_list.append((name, count))
                print(f'Built quiz: {output_path} ({count} questions)')
            except Exception as e:
                print(f'Error building quiz {questions_path}: {str(e)}')
        
        # 构建导航页
        self.build_index(quiz_list)
        print('Built index.html')

if __name__ == '__main__':
    builder = QuizBuilder('src/templates')
    builder.build() 