document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const currentDateElem = document.getElementById('current-date');
    const lunchMenuElem = document.getElementById('lunch-menu');
    const dinnerMenuElem = document.getElementById('dinner-menu');
    const prevDayButton = document.getElementById('prev-day');
    const nextDayButton = document.getElementById('next-day');
    const logoutButton = document.getElementById('logout-button');

    let currentDate = new Date();

    const fetchMealData = async (date) => {
        const dateString = date.toISOString().slice(0, 10).replace(/-/g, '');
        const response = await fetch(`/api/meal?date=${dateString}`);
        const data = await response.json();

        if (response.ok) {
            lunchMenuElem.textContent = data.lunch || '정보 없음';
            dinnerMenuElem.textContent = data.dinner || '정보 없음';
        } else {
            lunchMenuElem.textContent = '정보를 불러올 수 없습니다.';
            dinnerMenuElem.textContent = '정보를 불러올 수 없습니다.';
        }
        currentDateElem.textContent = date.toLocaleDateString('ko-KR');
    };

    prevDayButton.addEventListener('click', () => {
        currentDate.setDate(currentDate.getDate() - 1);
        fetchMealData(currentDate);
    });

    nextDayButton.addEventListener('click', () => {
        currentDate.setDate(currentDate.getDate() + 1);
        fetchMealData(currentDate);
    });

    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('token');
        window.location.href = '/login';
    });

    fetchMealData(currentDate);
});