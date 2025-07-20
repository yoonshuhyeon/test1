document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    const userName = localStorage.getItem('user_name');

    // 토큰 없으면 로그인 페이지로
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // 사용자 이름 표시
    document.getElementById('user-name').textContent = userName || '사용자';

    // 로그아웃 버튼
    document.getElementById('logout-button').addEventListener('click', () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user_name');
        window.location.href = '/login';
    });

    // 급식 정보 불러오기
    fetch('/api/meal', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const mealContent = document.getElementById('meal-content');
        if (data.error) {
            mealContent.innerHTML = `<div class="col-12"><div class="alert alert-warning">${data.error}</div></div>`;
            return;
        }

        let mealHtml = '';
        const meals = { 'lunch': '점심', 'dinner': '저녁' };

        for (const [type, name] of Object.entries(meals)) {
            mealHtml += `
                <div class="col-md-6 mb-3">
                    <div class="card meal-card h-100">
                        <div class="card-header">${name}</div>
                        <div class="card-body">
                            <ul class="list-unstyled mb-0">
                                ${data[type].split('\n').map(dish => `<li>${dish.trim()}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        }
        mealContent.innerHTML = mealHtml;
    })
    .catch(error => {
        console.error('Error fetching meal data:', error);
        const mealContent = document.getElementById('meal-content');
        mealContent.innerHTML = `<div class="col-12"><div class="alert alert-danger">급식 정보를 불러오는 중 오류가 발생했습니다.</div></div>`;
    });

    // 시간표 정보 불러오기
    fetch('/api/timetable', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const timetableContent = document.getElementById('timetable-content');
        if (data.error) {
            timetableContent.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
            return;
        }
        if (data.length === 0) {
            timetableContent.innerHTML = `<div class="alert alert-info">오늘의 시간표 정보가 없습니다.</div>`;
            return;
        }

        let tableHtml = '<table class="table table-bordered text-center timetable"><thead><tr>';
        const headers = [];
        const subjects = [];
        data.sort((a, b) => a.PERIO.localeCompare(b.PERIO)).forEach(item => {
            headers.push(`<th>${item.PERIO}교시</th>`);
            subjects.push(`<td>${item.ITRT_CNTNT}</td>`);
        });
        tableHtml += `${headers.join('')}</tr></thead><tbody><tr>${subjects.join('')}</tr></tbody></table>`;
        timetableContent.innerHTML = tableHtml;
    })
    .catch(error => {
        console.error('Error fetching timetable data:', error);
        const timetableContent = document.getElementById('timetable-content');
        timetableContent.innerHTML = `<div class="alert alert-danger">시간표 정보를 불러오는 중 오류가 발생했습니다.</div>`;
    });
}
