// 在Quiz类之前添加解析函数
function parseTxtQuestions(text) {
    const questions = [];
    const lines = text.split('\n');
    let currentQuestion = null;
    
    for (let line of lines) {
        line = line.trim();
        if (!line) continue;
        
        if (!line.startsWith('A') && !line.startsWith('B') && 
            !line.startsWith('C') && !line.startsWith('D')) {
            // 这是一个新题目
            if (currentQuestion) {
                questions.push(currentQuestion);
            }
            currentQuestion = {
                question: line,
                options: [],
                correctAnswer: null
            };
        } else {
            // 这是选项
            const option = line.substring(3).trim(); // 去掉"A. "这样的前缀
            currentQuestion.options.push(option);
            
            // 如果选项后面有"√"标记，则这是正确答案
            if (line.includes('√')) {
                currentQuestion.correctAnswer = currentQuestion.options.length - 1;
            }
        }
    }
    
    // 添加最后一个题目
    if (currentQuestion) {
        questions.push(currentQuestion);
    }
    
    return questions;
}

class Quiz {
    constructor(questions) {
        this.questions = this.shuffleQuestions(questions);
        this.currentQuestionIndex = 0;
        this.score = 0;
        this.userAnswers = new Array(questions.length).fill(null);
        this.timeLimit = 30 * 60; // 30分钟
        this.remainingTime = this.timeLimit;
        
        this.initializeElements();
        this.showQuestion();
        this.startTimer();
    }

    shuffleQuestions(questions) {
        const shuffled = [...questions];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
            // 打乱选项顺序
            shuffled[i].options = this.shuffleOptions(shuffled[i].options, shuffled[i].correctAnswer);
        }
        return shuffled;
    }

    shuffleOptions(options, correctAnswer) {
        const shuffled = [...options];
        const correctOption = options[correctAnswer];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        // 更新正确答案的索引
        this.questions[this.currentQuestionIndex].correctAnswer = shuffled.indexOf(correctOption);
        return shuffled;
    }

    initializeElements() {
        this.questionText = document.getElementById('question-text');
        this.optionsContainer = document.getElementById('options-container');
        this.prevButton = document.getElementById('prev-btn');
        this.nextButton = document.getElementById('next-btn');
        this.submitButton = document.getElementById('submit-btn');
        this.timeDisplay = document.getElementById('time');
        
        this.prevButton.addEventListener('click', () => this.previousQuestion());
        this.nextButton.addEventListener('click', () => this.nextQuestion());
        this.submitButton.addEventListener('click', () => this.submitQuiz());
    }

    showQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        this.questionText.textContent = `${this.currentQuestionIndex + 1}. ${question.question}`;
        
        this.optionsContainer.innerHTML = '';
        question.options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'option';
            button.textContent = `${String.fromCharCode(65 + index)}. ${option}`;
            
            if (this.userAnswers[this.currentQuestionIndex] === index) {
                button.classList.add('selected');
            }
            
            button.addEventListener('click', () => this.selectOption(index));
            this.optionsContainer.appendChild(button);
        });

        this.updateNavigationButtons();
    }

    selectOption(index) {
        this.userAnswers[this.currentQuestionIndex] = index;
        const options = this.optionsContainer.getElementsByClassName('option');
        Array.from(options).forEach(option => option.classList.remove('selected'));
        options[index].classList.add('selected');
    }

    previousQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.showQuestion();
        }
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.showQuestion();
        }
    }

    updateNavigationButtons() {
        this.prevButton.disabled = this.currentQuestionIndex === 0;
        if (this.currentQuestionIndex === this.questions.length - 1) {
            this.nextButton.style.display = 'none';
            this.submitButton.style.display = 'block';
        } else {
            this.nextButton.style.display = 'block';
            this.submitButton.style.display = 'none';
        }
    }

    startTimer() {
        const timer = setInterval(() => {
            this.remainingTime--;
            const minutes = Math.floor(this.remainingTime / 60);
            const seconds = this.remainingTime % 60;
            this.timeDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (this.remainingTime <= 0) {
                clearInterval(timer);
                this.submitQuiz();
            }
        }, 1000);
    }

    submitQuiz() {
        this.score = 0;
        this.userAnswers.forEach((answer, index) => {
            if (answer === this.questions[index].correctAnswer) {
                this.score++;
            }
        });

        document.getElementById('quiz').style.display = 'none';
        document.getElementById('results').style.display = 'block';
        document.getElementById('score').textContent = 
            `${this.score}/${this.questions.length} (${Math.round(this.score/this.questions.length*100)}%)`;
    }
}

// 初始化测验
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('txtFileInput');
    const startButton = document.getElementById('startQuiz');
    let quizInstance = null;

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const questions = parseTxtQuestions(e.target.result);
                if (questions.length > 0) {
                    startButton.style.display = 'block';
                    startButton.onclick = () => {
                        document.getElementById('quiz').style.display = 'block';
                        quizInstance = new Quiz(questions);
                        fileInput.style.display = 'none';
                        startButton.style.display = 'none';
                    };
                }
            };
            reader.readAsText(file);
        }
    });
}); 