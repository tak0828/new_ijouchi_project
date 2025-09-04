// static/js/login.js
document.addEventListener('DOMContentLoaded', () => {
    const login_btn = document.getElementById('login_btn');
    login_btn.addEventListener('click', () => {
        const loading_overlay = document.getElementById('loading_overlay');
        loading_overlay.style.display = 'block';
    });
});


