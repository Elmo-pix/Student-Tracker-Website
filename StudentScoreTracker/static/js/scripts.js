// Wait for the DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    // Handle question type change in the question form
    const questionTypeSelect = document.getElementById('question_type');
    if (questionTypeSelect) {
        questionTypeSelect.addEventListener('change', function() {
            toggleMultipleChoiceOptions(this.value);
        });
        
        // Initial toggle based on default value
        toggleMultipleChoiceOptions(questionTypeSelect.value);
    }
    
    // Set timer for quizzes if time_limit is specified
    const quizTimeLimit = document.getElementById('quiz-time-limit');
    if (quizTimeLimit) {
        const minutes = parseInt(quizTimeLimit.dataset.minutes);
        if (minutes > 0) {
            startQuizTimer(minutes);
        }
    }
    
    // Initialize any charts on the dashboard
    initializeCharts();
    
    // Add flash message auto-hide
    setTimeout(function() {
        const flashMessages = document.querySelectorAll('.alert');
        flashMessages.forEach(function(message) {
            const alert = new bootstrap.Alert(message);
            alert.close();
        });
    }, 5000);
});

// Toggle multiple choice options based on question type
function toggleMultipleChoiceOptions(questionType) {
    const multipleChoiceFields = document.querySelectorAll('.multiple-choice-field');
    if (questionType === 'multiple_choice') {
        multipleChoiceFields.forEach(field => field.style.display = 'block');
    } else {
        multipleChoiceFields.forEach(field => field.style.display = 'none');
    }
}

// Timer for quizzes
function startQuizTimer(minutes) {
    const timerDisplay = document.getElementById('timer-display');
    if (!timerDisplay) return;
    
    let totalSeconds = minutes * 60;
    
    const timerInterval = setInterval(function() {
        totalSeconds--;
        
        const minutesLeft = Math.floor(totalSeconds / 60);
        const secondsLeft = totalSeconds % 60;
        
        timerDisplay.textContent = `${minutesLeft.toString().padStart(2, '0')}:${secondsLeft.toString().padStart(2, '0')}`;
        
        if (totalSeconds <= 0) {
            clearInterval(timerInterval);
            document.getElementById('quiz-form').submit();
            alert('Time is up! Your answers have been submitted.');
        }
    }, 1000);
}

// Initialize charts for dashboard
function initializeCharts() {
    const attendanceChartCanvas = document.getElementById('attendanceChart');
    if (attendanceChartCanvas) {
        const ctx = attendanceChartCanvas.getContext('2d');
        
        // Get data from data attributes
        const presentCount = parseInt(attendanceChartCanvas.dataset.present || 0);
        const absentCount = parseInt(attendanceChartCanvas.dataset.absent || 0);
        const lateCount = parseInt(attendanceChartCanvas.dataset.late || 0);
        
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Present', 'Absent', 'Late'],
                datasets: [{
                    data: [presentCount, absentCount, lateCount],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(255, 206, 86, 0.7)'
                    ],
                    borderColor: [
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Attendance Summary'
                    }
                }
            }
        });
    }
    
    const performanceChartCanvas = document.getElementById('performanceChart');
    if (performanceChartCanvas) {
        const ctx = performanceChartCanvas.getContext('2d');
        
        // Get data from the canvas data attributes
        const quizNames = JSON.parse(performanceChartCanvas.dataset.quiznames || '[]');
        const quizScores = JSON.parse(performanceChartCanvas.dataset.quizscores || '[]');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: quizNames,
                datasets: [{
                    label: 'Quiz Scores',
                    data: quizScores,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Performance Summary'
                    }
                }
            }
        });
    }
}

// Confirm before deleting
function confirmDelete(formId, entityName) {
    if (confirm(`Are you sure you want to delete this ${entityName}? This action cannot be undone.`)) {
        document.getElementById(formId).submit();
    }
    return false;
}
