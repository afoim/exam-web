import os
import random
from datetime import datetime
import json
import re

class QuizFormatError(Exception):
    """题目格式错误的自定义异常"""
    pass

class QuizBuilder:
    def __init__(self, template_path, questions_path):
        self.template_path = template_path
        self.questions_path = questions_path
        
    def validate_question_format(self, line_num, line, question_data=None):
        """验证题目格式，有错误时抛出带有明确提示的异常"""
        # 验证题目行
        if line[0].isdigit():
            if '(' not in line or ')' not in line:
                raise QuizFormatError(f"第{line_num}行: 题目缺少正确答案标记，格式应为'题目内容( A )'")
            
            answer_start = line.find('(')
            answer_end = line.find(')')
            answers = line[answer_start+1:answer_end].strip()
            
            # 验证答案格式
            for ans in answers.split():
                if len(ans) != 1 or ans not in 'ABCD':
                    raise QuizFormatError(f"第{line_num}行: 正确答案'{ans}'无效，必须是A、B��C、D之")
        
        # 验选项行
        elif line[0] in 'ABCD':
            if len(line) < 2 or line[1] != '.':
                raise QuizFormatError(f"第{line_num}行: 选项格式错误，应为'A.选项内容'格式")
            
            if question_data and len(question_data['options']) >= 4:
                raise QuizFormatError(f"第{line_num}行: 该题选项数量超过4个")
        
        else:
            raise QuizFormatError(f"第{line_num}行: 无效的行格式，应以数字开头(题目)或A-D开头(选项)")

    def parse_options(self, line):
        """从包含制表符或多个空格的行中解析多个选项"""
        options = []
        
        # 调试信息
        print(f"正在解析选项行: {repr(line)}")
        
        # 移除所有前导空格和制表符
        line = line.strip()
        
        # 如果是单行包含所有选项的情况
        if 'A' in line and 'B' in line and 'C' in line and 'D' in line:
            # 先按制表符分割
            parts = line.split('\t')
            # 如果分割后的部分少于4个，尝试按多个空格分割
            if len(parts) < 4:
                import re
                parts = re.split(r'\s{2,}', line)
            
            # 处理每个部分
            for part in parts:
                part = part.strip()
                if part and part[0] in 'ABCD':
                    # 支持中英文点号
                    if len(part) > 1 and (part[1] == '.' or part[1] == '．'):
                        option_text = part[2:].strip()
                        if option_text:
                            options.append(option_text)
                    # 支持没有点号的格式
                    elif len(part) > 1:
                        option_text = part[1:].strip()
                        if option_text:
                            options.append(option_text)
        
        # 调试信息
        print(f"解析出的所有选项: {options}")
        
        return options

    def parse_questions(self):
        questions = []
        current_question = None
        line_num = 0
        question_num = 0
        processed_questions = set()  # 用于统计题目编号
        
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            total_lines = len(lines)
            print(f"总行数: {total_lines}")
            
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
                
                # 如果找到了答案，返后的答案和处理后的文本
                if answers:
                    return sorted(set(answers)), processed_text
                
                return None, line

            def is_question_line(line):
                """判断是否是题目行"""
                # 检查是否以数开头（持多个点号）
                if not any(c.isdigit() for c in line.split('.')[0].split('．')[0]):
                    return False
                # 检查是否包含括号和答案
                return ('(' in line and ')' in line) or ('（' in line and '）' in line)

            def is_option_line(line):
                """判断是否是选项行"""
                # 必须以A-D开头，后面跟着点号（支持中英文点号
                if not line or line[0] not in 'ABCD':
                    return False
                return len(line) > 1 and (line[1] == '.' or line[1] == '．')

            while line_num < len(lines):
                line = lines[line_num].strip()
                line_num += 1
                
                if not line:
                    continue
                
                # 记录题号并打印更详细的信息
                if line[0].isdigit():
                    try:
                        current_num = int(line.split('.')[0])
                        processed_questions.add(current_num)
                        print(f"\n处理题目 {current_num}: {line}")
                        # 打印接下来4行，看选项
                        for i in range(4):
                            if line_num + i < len(lines):
                                print(f"选项{i+1}: {lines[line_num + i].strip()}")
                    except ValueError:
                        pass
                
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
                                f"第{question_num}题（第{line_num}行）: 无法从题目中提取出有的答案，"
                                f"答案必须是A、B、C、D中的一个或多个")
                        
                        correct_answers = [ord(ans) - ord('A') for ans in answers]
                        is_multiple_choice = len(correct_answers) > 1
                        
                        # 移除题号
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
                            'correctAnswer': correct_answers,
                            'isMultipleChoice': is_multiple_choice,
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
                            
                            # 检查是否是包含多选项的行
                            if '\t' in next_line or '  ' in next_line:  # 同时检查制表符和多个空格
                                options = self.parse_options(next_line)
                                if options:
                                    # 调试信息
                                    print(f"发现选行: {next_line}")
                                    print(f"解析出的选项: {options}")
                                    
                                    for option in options:
                                        if option_count < 4:  # 确保不会添加超过4个项
                                            current_question['options'].append(option)
                                            option_count += 1
                                option_search_line_num += 1
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
                                f"第{question_num}题第{line_num}行）: 选项数量不足4个，实际只{option_count}个\n"
                                f"题目内容: {line}\n"
                                f"已找到的选项: {current_question['options']}"
                            )
                        
                        line_num = option_search_line_num  # 更新号到最后处理的位置
                    
                except QuizFormatError as e:
                    print(f"\n格式错误: {str(e)}")
                    print(f"出错的行内容: {line}")
                    print("\n正确的格式例:")
                    print("1.题内容( A )。")
                    print("2.题目内容（A）。  # 中文括号也支持")
                    print("3..题目内容( A )。  # 支持多个点号")
                    print("4.多选题内容( A B D )  # 多选题示例")
                    print("A.选1")
                    print("B.选项2")
                    print("C.选项3")
                    print("D.项4\n")
                    raise
        
        # 验证最后一题的完整性
        if current_question:
            if len(current_question['options']) != 4:
                raise QuizFormatError(
                    f"第{question_num}题（第{line_num}行）: 选不足4个，实际只有{len(current_question['options'])}")
            questions.append(current_question)
        
        if not questions:
            raise QuizFormatError("题目文件为空或格式错误")
        
        # 打印计息
        print("\n题目处理统计:")
        print(f"理的题目数量: {len(processed_questions)}")
        print(f"题目编号列表: {sorted(list(processed_questions))}")
        
        # 检查缺失的题号
        if processed_questions:
            max_num = max(processed_questions)
            missing = set(range(1, max_num + 1)) - processed_questions
            if missing:
                print(f"\n失的题号: {sorted(list(missing))}")
        
        return questions
    
    def build_questions_js(self, questions):
        def safe_json_dumps(obj):
            """自定义 JSON 列化，保留 HTML 标签"""
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
        
        # 印生成代码以便调试
        print("\n生成的 JavaScript 代码示例（第一题）:")
        print(js_questions[0] if js_questions else "没有题目")
        
        return js_code
    
    def build(self):
        # 读取模板
        with open(self.template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        # 解析题目
        questions = self.parse_questions()
        
        # 生成questions.js内容
        questions_js = self.build_questions_js(questions)
        
        # 将questions_js嵌入到模板中
        html = template.replace('// QUESTIONS_PLACEHOLDER', questions_js)
        
        # 确保dist目录存在
        os.makedirs('dist', exist_ok=True)
        
        # 生成index.html文件
        output_path = 'dist/index.html'
        
        # 写入生成HTML文
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f'Quiz built successfully: {output_path}')
    
    def generate_explanation(self, question, options, correct_answers):
        """生成题目解析"""
        # 构建解析文本
        explanation = "【解析】\n"
        explanation += "本题考查：...\n\n"
        explanation += "选项分析：\n"
        
        for i, option in enumerate(options):
            is_correct = i in correct_answers
            explanation += f"{chr(65 + i)}. {option}\n"
            explanation += f"   {'✓ ' if is_correct else '✗ '}"
            # 这里可以为每个选项添加具体分析
            explanation += "...\n"
        
        explanation += "\n答案解释：...\n"
        
        return explanation

if __name__ == '__main__':
    builder = QuizBuilder(
        template_path='src/templates/quiz_template.html',
        questions_path='src/questions.txt'
    )
    builder.build() 