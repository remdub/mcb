// Responsive canvas
function resizeCanvas() {
    const canvas = document.getElementById('quizCanvas');
    // Taille max 900x650, sinon 95vw/95vh
    let w = Math.min(window.innerWidth * 0.95, 900);
    let h = Math.min(window.innerHeight * 0.95, 650);
    canvas.width = w;
    canvas.height = h;
    if (typeof redrawScreen === 'function') redrawScreen();
}
window.addEventListener('resize', resizeCanvas);

// --- DONNÉES DU QUIZ VIA FICHIER JSON ---
let quizData = [];
let quizResults = {};
let quizIntro = {};
let quizLoaded = false;

function loadQuizData(callback) {
    const scriptTag = document.getElementById('quiz-script');
    const jsonFile = scriptTag.getAttribute('data-json');

    if (!jsonFile) {
        alert('Erreur : Le fichier JSON n\'est pas spécifié dans l\'attribut data-json de la balise script.');
        return;
    }

    fetch(jsonFile)
        .then(response => response.json())
        .then(data => {
            // Utilise directement le format du JSON
            if (data.title) {
                document.title = data.title;
            }
            if (data.quiz && data.quiz.questions) {
                quizData = data.quiz.questions.map(q => ({
                    question: q.question,
                    options: q.options,
                    correct: q.correct
                }));
            } else {
                quizData = [];
            }
            if (data.quiz && data.quiz.results) {
                quizResults = data.quiz.results;
            }
            if (data.quiz && data.quiz.intro) {
                quizIntro = data.quiz.intro;
            }
            quizLoaded = true;
            if (callback) callback();
        })
        .catch(err => {
            alert('Erreur de chargement du quiz : ' + err);
        });
}

// --- CONFIGURATION CANVAS ---
const canvas = document.getElementById('quizCanvas');
const ctx = canvas.getContext('2d');
// États du jeu
const STATE_START = 0;
const STATE_QUESTION = 1;
const STATE_FEEDBACK = 2;
const STATE_END = 3;
let currentState = STATE_START;
let currentQuestionIndex = 0;
let score = 0;
let selectedOption = -1;
// Zones cliquables (boutons)
let buttons = [];
// Pour redessiner l'écran après resize
function redrawScreen() {
    if (currentState === STATE_START) drawStartScreen();
    else if (currentState === STATE_QUESTION || currentState === STATE_FEEDBACK) drawQuestionScreen();
    else if (currentState === STATE_END) drawEndScreen();
}

// --- FONCTIONS DE DESSIN ---

function drawRoundedRect(x, y, w, h, r, color, strokeColor = null) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    if (strokeColor) {
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

function drawText(text, x, y, fontSize, color, align = "center", maxWidth = 0) {
    ctx.fillStyle = color;
    ctx.font = `${fontSize}px 'Segoe UI', Arial, sans-serif`;
    ctx.textAlign = align;
    
    if (maxWidth > 0) {
        const words = text.split(' ');
        let line = '';
        const lineHeight = fontSize * 1.4;
        let lines = [];
        
        for(let n = 0; n < words.length; n++) {
            const testLine = line + words[n] + ' ';
            const metrics = ctx.measureText(testLine);
            const testWidth = metrics.width;
            if (testWidth > maxWidth && n > 0) {
                lines.push(line);
                line = words[n] + ' ';
            } else {
                line = testLine;
            }
        }
        lines.push(line);
        
        // Dessiner les lignes
        let startY = y - ((lines.length - 1) * lineHeight) / 2; // Centrage vertical approximatif
        if (align === "left") startY = y; 

        for(let k = 0; k < lines.length; k++) {
            ctx.fillText(lines[k], x, startY + (k * lineHeight));
        }
        return lines.length * lineHeight; // Retourne la hauteur totale
    } else {
        ctx.fillText(text, x, y);
        return fontSize;
    }
}

// --- ÉCRANS ---

function drawStartScreen() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Fond
    drawRoundedRect(0, 0, canvas.width, canvas.height, 0, "#f8f9fa");
    // Responsive ratios
    const w = canvas.width, h = canvas.height;
    // Titre
    drawRoundedRect(w*0.17, h*0.12, w*0.66, h*0.15, 15, "#2c3e50");
    drawText(document.title, w/2, h*0.19, Math.round(h*0.055), "#ffffff");
    // Intro
    drawText(quizIntro.line1, w/2, h*0.38, Math.round(h*0.03), "#34495e");
    drawText(quizIntro.line2, w/2, h*0.44, Math.round(h*0.03), "#34495e");
    // Bouton Commencer
    const btnW = w*0.27, btnH = h*0.11;
    const btnX = w/2 - btnW/2;
    const btnY = h*0.62;
    drawRoundedRect(btnX, btnY, btnW, btnH, btnH/2, "#27ae60");
    drawText("COMMENCER", w/2, btnY + btnH*0.65, Math.round(h*0.037), "#ffffff");
    buttons = [{x: btnX, y: btnY, w: btnW, h: btnH, action: "start"}];
}

function drawQuestionScreen() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    buttons = [];
    
    const q = quizData[currentQuestionIndex];
    
    // Responsive ratios
    const w = canvas.width, h = canvas.height;
    // Barre de progression
    const progressHeight = Math.max(6, h*0.015);
    const progressWidth = w * ((currentQuestionIndex + 1) / quizData.length);
    ctx.fillStyle = "#ecf0f1";
    ctx.fillRect(0, 0, w, progressHeight);
    ctx.fillStyle = "#3498db";
    ctx.fillRect(0, 0, progressWidth, progressHeight);
    // Numéro question
    drawText(`Question ${currentQuestionIndex + 1} / ${quizData.length}`, w*0.05, h*0.07, Math.round(h*0.028), "#7f8c8d", "left");
    drawText(`Score: ${score}`, w*0.95, h*0.07, Math.round(h*0.028), "#27ae60", "right");
    // Texte Question
    const qBoxY = h*0.13;
    drawRoundedRect(w*0.055, qBoxY, w*0.89, h*0.18, 10, "#ffffff", "#bdc3c7");
    drawText(q.question, w/2, qBoxY + h*0.09, Math.round(h*0.037), "#2c3e50", "center", w*0.85);
    // Options
    const startY = h*0.38;
    const gap = h*0.10;
    const btnW = w*0.78, btnH = h*0.08;
    for (let i = 0; i < 4; i++) {
        const btnX = w*0.11;
        const btnY = startY + (i * gap);
        // Couleur par défaut
        let bgColor = "#ffffff";
        let textColor = "#2c3e50";
        let strokeColor = "#bdc3c7";
        // Gestion de l'état Feedback (après clic)
        if (currentState === STATE_FEEDBACK) {
            if (i === q.correct) {
                bgColor = "#2ecc71"; // Vert pour la bonne réponse
                textColor = "#ffffff";
                strokeColor = "#27ae60";
            } else if (i === selectedOption) {
                bgColor = "#e74c3c"; // Rouge si on a mal répondu
                textColor = "#ffffff";
                strokeColor = "#c0392b";
            } else {
                bgColor = "#ecf0f1"; // Grisé pour les autres
                textColor = "#95a5a6";
            }
        }
        drawRoundedRect(btnX, btnY, btnW, btnH, btnH/4, bgColor, strokeColor);
        drawText(q.options[i], btnX + btnH*0.3, btnY + btnH*0.62, Math.round(h*0.028), textColor, "left", btnW-btnH*0.5);
        if (currentState === STATE_QUESTION) {
            buttons.push({x: btnX, y: btnY, w: btnW, h: btnH, action: "answer", value: i});
        }
    }
    // Bouton Suivant (visible uniquement en feedback)
    if (currentState === STATE_FEEDBACK) {
        const nextBtnW = w*0.22, nextBtnH = h*0.07;
        const nextBtnX = w*0.72, nextBtnY = h*0.89;
        drawRoundedRect(nextBtnX, nextBtnY, nextBtnW, nextBtnH, nextBtnH/2, "#34495e");
        drawText(currentQuestionIndex < quizData.length - 1 ? "SUIVANT >" : "RÉSULTATS >", nextBtnX + nextBtnW/2, nextBtnY + nextBtnH*0.65, Math.round(h*0.028), "#ffffff");
        buttons.push({x: nextBtnX, y: nextBtnY, w: nextBtnW, h: nextBtnH, action: "next"});
        // Petit texte d'explication
        let msg = selectedOption === q.correct ? "Bonne réponse !" : "Dommage !";
        drawText(msg, w/2, nextBtnY - h*0.02, Math.round(h*0.033), selectedOption === q.correct ? "#27ae60" : "#e74c3c");
    }
}

function drawEndScreen() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Responsive ratios
    const w = canvas.width, h = canvas.height;
    drawRoundedRect(0, 0, w, h, 0, "#f8f9fa");
    // Titre
    drawText("Quiz terminé !", w/2, h*0.23, Math.round(h*0.062), "#2c3e50");
    // Score
    drawText(`Votre score : ${score} / ${quizData.length}`, w/2, h*0.38, Math.round(h*0.073), "#2980b9");
    // Message selon score
    let message = "";
    if (score === 10) message = quizResults.excellent;
    else if (score >= 7) message = quizResults.good;
    else if (score >= 5) message = quizResults.average;
    else message = quizResults.bad;
    drawText(message, w/2, h*0.49, Math.round(h*0.03), "#7f8c8d");
    // Bouton Rejouer
    const btnW = w*0.22, btnH = h*0.09;
    const btnX = w/2 - btnW/2;
    const btnY = h*0.7;
    drawRoundedRect(btnX, btnY, btnW, btnH, btnH/2, "#3498db");
    drawText("REJOUER", w/2, btnY + btnH*0.63, Math.round(h*0.037), "#ffffff");
    buttons = [{x: btnX, y: btnY, w: btnW, h: btnH, action: "restart"}];
}

// --- LOGIQUE ---

function handleInput(x, y) {
    // Vérifier clic sur un bouton
    for (let btn of buttons) {
        if (x >= btn.x && x <= btn.x + btn.w && y >= btn.y && y <= btn.y + btn.h) {
            // Curseurs mains
            canvas.style.cursor = "pointer";
            
            if (btn.action === "start") {
                currentState = STATE_QUESTION;
                currentQuestionIndex = 0;
                score = 0;
                drawQuestionScreen();
            } 
            else if (btn.action === "answer") {
                selectedOption = btn.value;
                currentState = STATE_FEEDBACK;
                if (selectedOption === quizData[currentQuestionIndex].correct) {
                    score++;
                }
                drawQuestionScreen();
            }
            else if (btn.action === "next") {
                if (currentQuestionIndex < quizData.length - 1) {
                    currentQuestionIndex++;
                    currentState = STATE_QUESTION;
                    drawQuestionScreen();
                } else {
                    currentState = STATE_END;
                    drawEndScreen();
                }
            }
            else if (btn.action === "restart") {
                currentState = STATE_START;
                drawStartScreen();
            }
            return;
        }
    }
}

// --- ÉVÉNEMENTS ---

canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    handleInput(x, y);
});

canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    let hovering = false;
    for (let btn of buttons) {
        if (x >= btn.x && x <= btn.x + btn.w && y >= btn.y && y <= btn.y + btn.h) {
            hovering = true;
        }
    }
    canvas.style.cursor = hovering ? "pointer" : "default";
});

// Démarrage : charger les données puis afficher l'écran de démarrage
function startQuiz() {
    resizeCanvas();
    drawStartScreen();
}
loadQuizData(startQuiz);
// Initial resize au cas où
window.addEventListener('DOMContentLoaded', resizeCanvas);