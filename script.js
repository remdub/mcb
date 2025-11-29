document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENTS ---
    const quizContainer = document.getElementById('quiz-container');
    const startScreen = document.getElementById('start-screen');
    const questionScreen = document.getElementById('question-screen');
    const endScreen = document.getElementById('end-screen');

    const quizTitle = document.getElementById('quiz-title');
    const introLine1 = document.getElementById('intro-line1');
    const introLine2 = document.getElementById('intro-line2');
    const startButton = document.getElementById('start-button');

    const progressBar = document.getElementById('progress-bar');
    const questionCounter = document.getElementById('question-counter');
    const scoreDisplay = document.getElementById('score-display');
    const questionText = document.getElementById('question-text');
    const answerOptions = document.getElementById('answer-options');
    const feedbackSection = document.getElementById('feedback-section');
    const feedbackText = document.getElementById('feedback-text');
    const nextButton = document.getElementById('next-button');
    
    const finalScore = document.getElementById('final-score');
    const totalQuestions = document.getElementById('total-questions');
    const endMessage = document.getElementById('end-message');
    const replayButton = document.getElementById('replay-button');

    // --- QUIZ STATE ---
    let quizData = [];
    let quizResults = {};
    let quizIntro = {};
    
    let currentQuestionIndex = 0;
    let score = 0;

    // --- FUNCTIONS ---

    function loadQuizData() {
        const scriptTag = document.getElementById('quiz-script');
        const jsonFile = scriptTag.getAttribute('data-json');

        if (!jsonFile) {
            quizContainer.innerHTML = '<p style="color: red; text-align: center;">Erreur: Fichier JSON non spécifié.</p>';
            return;
        }

        fetch(jsonFile)
            .then(response => response.json())
            .then(data => {
                document.title = data.title || 'Quiz';
                quizData = data.quiz.questions || [];
                quizResults = data.quiz.results || {};
                quizIntro = data.quiz.intro || {};
                
                if (quizData.length > 0) {
                    setupStartScreen();
                } else {
                    quizContainer.innerHTML = '<p style="color: red; text-align: center;">Erreur: Aucune question trouvée dans le fichier.</p>';
                }
            })
            .catch(error => {
                console.error('Erreur de chargement du quiz:', error);
                quizContainer.innerHTML = `<p style="color: red; text-align: center;">Erreur de chargement du fichier du quiz. Vérifiez la console pour plus de détails.</p>`;
            });
    }
    
    function setupStartScreen() {
        quizTitle.textContent = document.title;
        introLine1.textContent = quizIntro.line1 || '';
        introLine2.textContent = quizIntro.line2 || '';
        showScreen('start');
    }

    function startQuiz() {
        currentQuestionIndex = 0;
        score = 0;
        showQuestion();
    }

    function showQuestion() {
        feedbackSection.style.visibility = 'hidden';
        answerOptions.childNodes.forEach(child => child.disabled = false);

        const question = quizData[currentQuestionIndex];
        
        // Update progress
        const progress = ((currentQuestionIndex) / quizData.length) * 100;
        progressBar.style.setProperty('--progress', `${progress}%`);
        questionCounter.textContent = `Question ${currentQuestionIndex + 1} / ${quizData.length}`;
        scoreDisplay.textContent = `Score: ${score}`;

        // Populate question and answers
        questionText.textContent = question.question;
        answerOptions.innerHTML = '';

        question.options.forEach((optionText, index) => {
            const button = document.createElement('button');
            button.textContent = optionText;
            button.dataset.index = index;
            button.addEventListener('click', handleAnswer);
            answerOptions.appendChild(button);
        });

        showScreen('question');
    }

    function handleAnswer(event) {
        const selectedButton = event.target;
        const selectedAnswerIndex = parseInt(selectedButton.dataset.index, 10);
        const correctAnswerIndex = quizData[currentQuestionIndex].correct;

        // Disable all buttons
        answerOptions.childNodes.forEach(child => child.disabled = true);
        
        if (selectedAnswerIndex === correctAnswerIndex) {
            score++;
            selectedButton.classList.add('correct');
            feedbackText.textContent = "Bonne réponse !";
            feedbackText.className = 'correct';
        } else {
            selectedButton.classList.add('incorrect');
            answerOptions.childNodes[correctAnswerIndex].classList.add('correct');
            feedbackText.textContent = "Dommage !";
            feedbackText.className = 'incorrect';
        }
        
        scoreDisplay.textContent = `Score: ${score}`;
        feedbackSection.style.visibility = 'visible';

        if (currentQuestionIndex === quizData.length - 1) {
            nextButton.textContent = 'RÉSULTATS';
        } else {
            nextButton.textContent = 'SUIVANT';
        }
    }
    
    function showNext() {
        currentQuestionIndex++;
        if (currentQuestionIndex < quizData.length) {
            showQuestion();
            // Reset button styles and feedback
            answerOptions.childNodes.forEach(button => button.className = '');
            feedbackSection.style.visibility = 'hidden';
        } else {
            showEndScreen();
        }
    }

    function showEndScreen() {
        finalScore.textContent = score;
        totalQuestions.textContent = quizData.length;

        let message = '';
        const scorePercent = score / quizData.length;

        if (scorePercent === 1) message = quizResults.excellent || "Excellent!";
        else if (scorePercent >= 0.7) message = quizResults.good || "Très bien !";
        else if (scorePercent >= 0.5) message = quizResults.average || "Pas mal.";
        else message = quizResults.bad || "Il faut revoir la matière.";
        
        endMessage.textContent = message;
        
        showScreen('end');
    }

    function showScreen(screenName) {
        startScreen.classList.add('hidden');
        questionScreen.classList.add('hidden');
        endScreen.classList.add('hidden');
        
        document.getElementById(`${screenName}-screen`).classList.remove('hidden');
    }

    // --- EVENT LISTENERS ---
    startButton.addEventListener('click', startQuiz);
    nextButton.addEventListener('click', showNext);
    replayButton.addEventListener('click', startQuiz);

    // --- INITIALIZATION ---
    loadQuizData();
});
