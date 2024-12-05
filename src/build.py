import os
import random
from datetime import datetime
import json

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
                    raise QuizFormatError(f"第{line_num}行: 正确答案'{ans}'无效，必须是A、B、C、D之")
        
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
        
        # 如果是单行包含所有选项的情况（用空格分隔）
        if 'A' in line and 'B' in line and 'C' in line and 'D' in line:
            import re
            # 使用正则表达式匹配所有选项
            # 先将行按选项标记分割
            parts = re.split(r'([A-D][\. ])', line)
            current_option = None
            current_text = []
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                if re.match(r'^[A-D][\. ]$', part):  # 如果是选项标记
                    if current_option is not None and current_text:
                        options.append(''.join(current_text).strip())
                        current_text = []
                    current_option = part[0]
                else:
                    if current_option is not None:
                        current_text.append(part)
            
            # 添加最后一个选项
            if current_option is not None and current_text:
                options.append(''.join(current_text).strip())
            
            if len(options) == 4:  # 如果找到了4个选项，直接返回
                return options
        
        # 如果上面的方法没有找到4个选项，尝试按制表符分割
        if not options:
            parts = line.split('\t')
            for part in parts:
                part = part.strip()
                if part and part[0] in 'ABCD' and len(part) > 1:
                    # 找到第一个点号后的位置
                    option_start = 2 if part[1] in '.．' else 1
                    option_text = part[option_start:].strip()
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
        
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            def extract_answer(text, line):
                """从文本中提取答案，如果找不到则尝试在整行中查找"""
                # 首先尝试从括号内容中提取
                answers = []
                for char in text:
                    if char in 'ABCD':
                        answers.append(char)
                
                # 如果括号内没有找到答案，尝试查找其他括号
                if not answers:
                    # 查找所有括号对
                    brackets = []
                    for i, char in enumerate(line):
                        if char in '(（':
                            brackets.append((i, char))
                        elif char in ')）' and brackets:
                            start_idx, start_char = brackets.pop()
                            # 检查这对括号内的内容
                            bracket_content = line[start_idx+1:i]
                            for c in bracket_content:
                                if c in 'ABCD':
                                    answers.append(c)
                            if answers:  # 如果找到答案就停止查找
                                break
                
                return answers if answers else None

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
                        
                        # 提取题目和答案（支持中英文括号）
                        answer_start = -1
                        answer_end = -1
                        
                        # 检查英���括号
                        if '(' in line and ')' in line:
                            answer_start = line.find('(')
                            answer_end = line.find(')')
                        # 检查中文括号
                        elif '（' in line and '）' in line:
                            answer_start = line.find('（')
                            answer_end = line.find('）')
                        
                        if answer_start == -1 or answer_end == -1:
                            raise QuizFormatError(f"第{question_num}题（第{line_num}行）: 题目缺少正确答案标记，格式为'题目内( A )'或'题目内容（A）'")
                        
                        # 提取并验证答案
                        answers_text = line[answer_start+1:answer_end]
                        answers = extract_answer(answers_text, line)
                        
                        if not answers:
                            raise QuizFormatError(
                                f"第{question_num}题（第{line_num}行）: 无法从'{answers_text}'中提取出有效的答案(A/B/C/D)")
                        
                        correct_answers = [ord(ans) - ord('A') for ans in answers]
                        is_multiple_choice = len(correct_answers) > 1
                        
                        # 不对HTML标签进行转义
                        question_text = line[:answer_start].strip()
                        current_question = {
                            'question': question_text,
                            'options': [],
                            'correctAnswer': correct_answers,
                            'isMultipleChoice': is_multiple_choice
                        }
                        
                        # 向前查找选项
                        option_count = 0
                        option_search_line_num = line_num
                        while option_count < 4 and option_search_line_num < len(lines):
                            next_line = lines[option_search_line_num].strip()
                            if not next_line:
                                option_search_line_num += 1
                                continue
                            
                            # 检查是否是包含多个选项的行
                            if '\t' in next_line or '  ' in next_line:  # 同时检查制表符和多个空格
                                options = self.parse_options(next_line)
                                if options:
                                    # 调试信息
                                    print(f"发现选项行: {next_line}")
                                    print(f"解析出的选项: {options}")
                                    
                                    for option in options:
                                        if option_count < 4:  # 确保不会添加超过4个选项
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
                    print("2.题目容（A）。  # 中文括号也支持")
                    print("3..题目内容( A )。  # 支持多个点号")
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
        js_questions = []
        for q in questions:
            # 使用 JSON.stringify，但确保 HTML 标签不被转义
            js_questions.append(f"""{{
                question: {json.dumps(q['question'], ensure_ascii=False)},
                options: {json.dumps(q['options'], ensure_ascii=False)},
                correctAnswer: {q['correctAnswer']},
                isMultipleChoice: {str(q['isMultipleChoice']).lower()}
            }}""")
            
        return "const questions = [\n    " + ",\n    ".join(js_questions) + "\n];"
    
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
        
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'dist/quiz_{timestamp}.html'
        
        # 写入生成的HTML件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f'Quiz built successfully: {output_path}')

if __name__ == '__main__':
    builder = QuizBuilder(
        template_path='src/templates/quiz_template.html',
        questions_path='src/questions.txt'
    )
    builder.build() 