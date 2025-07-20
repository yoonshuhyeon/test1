document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const response = await fetch('/api/generate_qr', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    const data = await response.json();

    if (response.ok) {
        new QRCode(document.getElementById('qr-code'), {
            text: data.qr_code_url,
            width: 256,
            height: 256,
        });
    } else {
        alert(data.error);
    }
});