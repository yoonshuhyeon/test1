document.getElementById('signup-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const name = document.getElementById('name').value;
    const grade = document.getElementById('grade').value;
    const class_number = document.getElementById('class_number').value;
    const student_number = document.getElementById('student_number').value;

    const response = await fetch('/api/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password, name, grade, class_number, student_number })
    });

    const data = await response.json();

    if (response.ok) {
        alert(data.message);
        window.location.href = '/login';
    } else {
        alert(data.error);
    }
});