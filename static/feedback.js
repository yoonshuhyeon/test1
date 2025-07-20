document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const dateInput = document.getElementById('feedback-date');
    const mealTypeSelect = document.getElementById('meal-type');
    const menuElem = document.getElementById('feedback-menu');
    const likeButton = document.getElementById('like-button');
    const likeCountElem = document.getElementById('like-count');

    dateInput.valueAsDate = new Date();

    const fetchFeedbackData = async () => {
        const date = dateInput.value.replace(/-/g, '');
        const meal_type = mealTypeSelect.value;

        // Fetch meal info
        const mealResponse = await fetch(`/api/meal?date=${date}`);
        const mealData = await mealResponse.json();
        if (mealResponse.ok) {
            menuElem.textContent = mealData[meal_type] || '정보 없음';
        } else {
            menuElem.textContent = '정보를 불러올 수 없습니다.';
        }

        // Fetch like count
        const likeResponse = await fetch(`/api/get_like_count?date=${date}&meal_type=${meal_type}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const likeData = await likeResponse.json();
        if (likeResponse.ok) {
            likeCountElem.textContent = likeData.like_count;
            likeButton.textContent = likeData.user_has_liked ? '좋아요 취소' : '좋아요';
        } else {
            likeCountElem.textContent = '0';
        }
    };

    likeButton.addEventListener('click', async () => {
        const date = dateInput.value.replace(/-/g, '');
        const meal_type = mealTypeSelect.value;

        const response = await fetch('/api/submit_like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ date, meal_type })
        });

        if (response.ok) {
            fetchFeedbackData();
        } else {
            const data = await response.json();
            alert(data.error);
        }
    });

    dateInput.addEventListener('change', fetchFeedbackData);
    mealTypeSelect.addEventListener('change', fetchFeedbackData);

    fetchFeedbackData();
});