document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const response = await fetch('/api/nutrition');
    const data = await response.json();

    if (response.ok) {
        document.getElementById('orplc-info').textContent = data.ORPLC_INFO;
        document.getElementById('cal-info').textContent = data.CAL_INFO;
        document.getElementById('ntr-info').textContent = data.NTR_INFO;
        document.getElementById('allergy-info').textContent = data.allergy;
    } else {
        alert(data.error);
    }
});