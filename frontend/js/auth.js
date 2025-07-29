// Authentication JavaScript
class AuthManager {
    constructor() {
        this.initializeEventListeners();
        this.checkSession();
        this.initializeCarousel();
    }

    initializeEventListeners() {
        // Form submission
        const loginForm = document.getElementById('loginForm');
        loginForm.addEventListener('submit', this.handleLogin.bind(this));

        // Password toggle
        const togglePassword = document.getElementById('togglePassword');
        togglePassword.addEventListener('click', this.togglePasswordVisibility.bind(this));

        // Real-time validation
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        
        usernameInput.addEventListener('blur', () => this.validateUsername(usernameInput.value));
        passwordInput.addEventListener('blur', () => this.validatePassword(passwordInput.value));
        
        // Clear errors on input
        usernameInput.addEventListener('input', () => this.clearError('usernameError'));
        passwordInput.addEventListener('input', () => this.clearError('passwordError'));
    }

    async checkSession() {
        try {
            const response = await fetch('/auth/check-session');
            const data = await response.json();
            
            if (data.authenticated) {
                window.location.href = '/dashboard.html';
            }
        } catch (error) {
            console.log('No active session');
        }
    }

    validateUsername(username) {
        const errorElement = document.getElementById('usernameError');
        
        if (!username) {
            this.showError('usernameError', 'Username is required');
            return false;
        } else if (username.length < 3) {
            this.showError('usernameError', 'Username must be at least 3 characters long');
            return false;
        } else {
            this.clearError('usernameError');
            return true;
        }
    }

    validatePassword(password) {
        const errorElement = document.getElementById('passwordError');
        
        if (!password) {
            this.showError('passwordError', 'Password is required');
            return false;
        } else if (password.length < 6) {
            this.showError('passwordError', 'Password must be at least 6 characters long');
            return false;
        } else {
            this.clearError('passwordError');
            return true;
        }
    }

    showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    clearError(elementId) {
        const errorElement = document.getElementById(elementId);
        errorElement.textContent = '';
        errorElement.classList.remove('show');
    }

    showAlert(message, type = 'error') {
        const alertElement = document.getElementById('alertMessage');
        alertElement.textContent = message;
        alertElement.className = `alert ${type}`;
        alertElement.classList.remove('hidden');
        
        // Auto hide success messages
        if (type === 'success') {
            setTimeout(() => {
                alertElement.classList.add('hidden');
            }, 3000);
        }
    }

    hideAlert() {
        const alertElement = document.getElementById('alertMessage');
        alertElement.classList.add('hidden');
    }

    setLoading(loading = true) {
        const loginBtn = document.getElementById('loginBtn');
        const btnText = loginBtn.querySelector('.btn-text');
        const btnLoader = loginBtn.querySelector('.btn-loader');
        
        if (loading) {
            loginBtn.disabled = true;
            loginBtn.classList.add('loading');
            btnText.style.opacity = '0';
            btnLoader.classList.remove('hidden');
        } else {
            loginBtn.disabled = false;
            loginBtn.classList.remove('loading');
            btnText.style.opacity = '1';
            btnLoader.classList.add('hidden');
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        this.hideAlert();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        // Validate inputs
        const isUsernameValid = this.validateUsername(username);
        const isPasswordValid = this.validatePassword(password);

        if (!isUsernameValid || !isPasswordValid) {
            return;
        }

        this.setLoading(true);

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert('Login successful! Redirecting...', 'success');
                
                // Small delay to show success message
                setTimeout(() => {
                    window.location.href = data.redirect || '/dashboard.html';
                }, 1000);
            } else {
                this.showAlert(data.message || 'Login failed. Please try again.');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showAlert('Network error. Please check your connection and try again.');
        } finally {
            this.setLoading(false);
        }
    }

    togglePasswordVisibility() {
        const passwordInput = document.getElementById('password');
        const toggleIcon = document.querySelector('#togglePassword i');
        
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleIcon.classList.replace('fa-eye', 'fa-eye-slash');
        } else {
            passwordInput.type = 'password';
            toggleIcon.classList.replace('fa-eye-slash', 'fa-eye');
        }
    }

    // Carousel functionality
    initializeCarousel() {
        this.currentSlide = 0;
        this.totalSlides = 6; // EPCG, CANU, CGES, Meteo, CEDIS, Tehnopolis
        this.autoSlideInterval = 4000; // 4 seconds
        this.progressInterval = null;
        this.autoSlideTimer = null;

        // Get DOM elements
        this.carouselTrack = document.getElementById('carouselTrack');
        this.progressBar = document.getElementById('progressBar');
        this.dots = document.querySelectorAll('.dot');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');

        // Add event listeners
        this.prevBtn.addEventListener('click', () => this.previousSlide());
        this.nextBtn.addEventListener('click', () => this.nextSlide());
        
        this.dots.forEach((dot, index) => {
            dot.addEventListener('click', () => this.goToSlide(index));
        });

        // Start auto-slide
        this.startAutoSlide();

        // Pause on hover
        const carouselContainer = document.querySelector('.carousel-container');
        carouselContainer.addEventListener('mouseenter', () => this.pauseAutoSlide());
        carouselContainer.addEventListener('mouseleave', () => this.startAutoSlide());
    }

    goToSlide(slideIndex) {
        this.currentSlide = slideIndex;
        this.updateCarousel();
        this.resetProgress();
    }

    nextSlide() {
        this.currentSlide = (this.currentSlide + 1) % this.totalSlides;
        this.updateCarousel();
        this.resetProgress();
    }

    previousSlide() {
        this.currentSlide = (this.currentSlide - 1 + this.totalSlides) % this.totalSlides;
        this.updateCarousel();
        this.resetProgress();
    }

    updateCarousel() {
        // Move carousel
        const translateX = -this.currentSlide * 100;
        this.carouselTrack.style.transform = `translateX(${translateX}%)`;

        // Update dots
        this.dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === this.currentSlide);
        });
    }

    startAutoSlide() {
        this.clearTimers();
        this.startProgress();
        
        this.autoSlideTimer = setInterval(() => {
            this.nextSlide();
        }, this.autoSlideInterval);
    }

    pauseAutoSlide() {
        this.clearTimers();
        this.progressBar.style.width = '0%';
    }

    startProgress() {
        let progress = 0;
        const increment = 100 / (this.autoSlideInterval / 50); // Update every 50ms
        
        this.progressInterval = setInterval(() => {
            progress += increment;
            this.progressBar.style.width = `${Math.min(progress, 100)}%`;
            
            if (progress >= 100) {
                clearInterval(this.progressInterval);
            }
        }, 50);
    }

    resetProgress() {
        this.clearTimers();
        this.progressBar.style.width = '0%';
        
        setTimeout(() => {
            this.startAutoSlide(); // Restart auto-slide instead of just progress
        }, 100);
    }

    clearTimers() {
        if (this.autoSlideTimer) {
            clearInterval(this.autoSlideTimer);
            this.autoSlideTimer = null;
        }
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});

// Add some electric effects
document.addEventListener('DOMContentLoaded', () => {
    // Electric spark effect on successful login
    function createSparkEffect() {
        const sparks = document.createElement('div');
        sparks.className = 'electric-sparks';
        sparks.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            width: 100px;
            height: 100px;
            pointer-events: none;
            z-index: 9999;
            transform: translate(-50%, -50%);
        `;
        
        for (let i = 0; i < 12; i++) {
            const spark = document.createElement('div');
            spark.style.cssText = `
                position: absolute;
                width: 4px;
                height: 4px;
                background: #3b82f6;
                border-radius: 50%;
                box-shadow: 0 0 10px #3b82f6;
                animation: spark-${i} 0.8s ease-out forwards;
            `;
            
            const angle = (360 / 12) * i;
            const distance = 50;
            const x = Math.cos(angle * Math.PI / 180) * distance;
            const y = Math.sin(angle * Math.PI / 180) * distance;
            
            spark.style.setProperty('--end-x', `${x}px`);
            spark.style.setProperty('--end-y', `${y}px`);
            
            // Create keyframes for this spark
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spark-${i} {
                    0% {
                        transform: translate(0, 0) scale(1);
                        opacity: 1;
                    }
                    100% {
                        transform: translate(${x}px, ${y}px) scale(0);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
            
            sparks.appendChild(spark);
        }
        
        document.body.appendChild(sparks);
        
        setTimeout(() => {
            document.body.removeChild(sparks);
        }, 1000);
    }
    
    // Add to successful login
    const originalShowAlert = window.authManager?.showAlert;
    if (window.authManager) {
        window.authManager.showAlert = function(message, type = 'error') {
            if (originalShowAlert) {
                originalShowAlert.call(this, message, type);
            }
            if (type === 'success') {
                createSparkEffect();
            }
        };
    }
});
