document.getElementById('login-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');

    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('user_name', data.user_name);
            window.location.href = '/'; // 메인 페이지로 이동
        } else {
            errorMessage.textContent = data.error || '로그인에 실패했습니다.';
            errorMessage.classList.remove('d-none');
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        errorMessage.textContent = '로그인 중 오류가 발생했습니다.';
        errorMessage.classList.remove('d-none');
    });
});