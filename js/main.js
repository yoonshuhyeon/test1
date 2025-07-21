document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    const userName = localStorage.getItem('user_name');

    // 사용자 이름 표시 (로그인 상태일 경우)
    const userNameElement = document.getElementById('user-name');
    const logoutButton = document.getElementById('logout-button');
    const loginButtonContainer = document.getElementById('login-button-container');

    if (userNameElement && logoutButton && loginButtonContainer) {
        if (userName) {
            userNameElement.textContent = userName;
            logoutButton.style.display = 'inline-block';
            loginButtonContainer.style.display = 'none';
        } else {
            userNameElement.textContent = '';
            logoutButton.style.display = 'none';
            loginButtonContainer.style.display = 'inline-block';
        }
    }

    // 로그아웃 버튼
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            localStorage.removeItem('token');
            localStorage.removeItem('user_name');
            window.location.href = '/';
        });
    }

    // 날짜를 YYYYMMDD 형식으로 포맷하는 함수
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}${month}${day}`;
    }

    // 날짜를 YYYY-MM-DD 형식으로 포맷하는 함수 (input[type="date"]용)
    function formatInputDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 급식 정보 불러오는 함수
    function fetchMealData(dateStr) {
        const mealContent = document.getElementById('meal-content');
        mealContent.innerHTML = `
            <div class="col-12 text-center p-5">
                <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `; // 로딩 스피너 표시

        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        fetch(`/api/meal?date=${dateStr}`, { headers: headers })
        .then(response => response.json())
        .then(data => {
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
            mealContent.innerHTML = `<div class="col-12"><div class="alert alert-danger">급식 정보를 불러오는 중 오류가 발생했습니다.</div></div>`;
        });
    }

    // Helper to get the Monday of the week for a given date
    function getMonday(d) {
        d = new Date(d);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Sunday (0)
        return new Date(d.setDate(diff));
    }

    // 시간표 정보 불러오는 함수 (주간 시간표)
    async function fetchWeeklyTimetableData(grade, classNumber, selectedDate) {
        const timetableContent = document.getElementById('timetable-content');
        timetableContent.innerHTML = `
            <div class="col-12 text-center p-5">
                <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `; // 로딩 스피너 표시

        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const monday = getMonday(selectedDate);
        const weeklyData = {}; // { 'YYYYMMDD': [{PERIO: '1', ITRT_CNTNT: '수학'}, ...], ... }

        try {
            for (let i = 0; i < 5; i++) { // Monday to Friday
                const currentDay = new Date(monday);
                currentDay.setDate(monday.getDate() + i);
                const dateStr = formatDate(currentDay);

                const response = await fetch(`/api/timetable?date=${dateStr}&grade=${grade}&class_number=${classNumber}`, { headers: headers });
                const data = await response.json();

                if (data.error) {
                    // Handle error for individual day, but continue fetching other days
                    console.error(`Error fetching timetable for ${dateStr}:`, data.error);
                    weeklyData[dateStr] = { error: data.error };
                } else if (data.length === 0) {
                    weeklyData[dateStr] = { empty: true };
                } else {
                    weeklyData[dateStr] = data.sort((a, b) => a.PERIO.localeCompare(b.PERIO));
                }
            }

            // Calculate start and end dates for the week display
            const firstDayOfWeek = new Date(monday);
            const lastDayOfWeek = new Date(monday);
            lastDayOfWeek.setDate(monday.getDate() + 4); // Friday

            const weekRangeDisplay = `${firstDayOfWeek.getFullYear()}.` +
                                     `${String(firstDayOfWeek.getMonth() + 1).padStart(2, '0')}.` +
                                     `${String(firstDayOfWeek.getDate()).padStart(2, '0')} ~ ` +
                                     `${lastDayOfWeek.getFullYear()}.` +
                                     `${String(lastDayOfWeek.getMonth() + 1).padStart(2, '0')}.` +
                                     `${String(lastDayOfWeek.getDate()).padStart(2, '0')}`;

            let tableHtml = `<h5 class="text-center mb-3">${weekRangeDisplay} 주간 시간표</h5>`;
            tableHtml += '<table class="table table-bordered text-center timetable"><thead><tr>';
            tableHtml += '<th>교시</th>';
            const daysOfWeek = ['월', '화', '수', '목', '금'];
            const datesInWeek = [];
            for (let i = 0; i < 5; i++) {
                const currentDay = new Date(monday);
                currentDay.setDate(monday.getDate() + i);
                datesInWeek.push(formatDate(currentDay));
                tableHtml += `<th>${daysOfWeek[i]} (${currentDay.getMonth() + 1}/${currentDay.getDate()})</th>`;
            }
            tableHtml += '</tr></thead><tbody>';

            // Assuming max 7 periods for simplicity, adjust if needed
            for (let period = 1; period <= 7; period++) {
                tableHtml += `<tr><td>${period}교시</td>`;
                for (const date of datesInWeek) {
                    const dayData = weeklyData[date];
                    let subject = '';
                    if (dayData && !dayData.error && !dayData.empty) {
                        const periodEntry = dayData.find(item => parseInt(item.PERIO) === period);
                        subject = periodEntry && periodEntry.ITRT_CNTNT ? periodEntry.ITRT_CNTNT : '';
                    } else if (dayData && dayData.error) {
                        subject = '오류';
                    } else if (dayData && dayData.empty) {
                        subject = '정보 없음';
                    }
                    tableHtml += `<td>${subject}</td>`;
                }
                tableHtml += '</tr>';
            }
            tableHtml += '</tbody></table>';
            timetableContent.innerHTML = tableHtml;

        } catch (error) {
            console.error('Error fetching weekly timetable data:', error);
            timetableContent.innerHTML = `<div class="alert alert-danger">주간 시간표 정보를 불러오는 중 오류가 발생했습니다.</div>`;
        }
    }

    // 급식 날짜 입력 필드 설정 및 이벤트 리스너
    const mealDateInput = document.getElementById('meal-date');
    const today = new Date();
    mealDateInput.value = formatInputDate(today);
    fetchMealData(formatDate(today)); // 초기 급식 정보 로드

    mealDateInput.addEventListener('change', () => {
        fetchMealData(formatDate(new Date(mealDateInput.value)));
    });

    // 시간표 날짜 입력 필드 설정
    const timetableDateInput = document.getElementById('timetable-date');
    timetableDateInput.value = formatInputDate(today);

    // Initial load of weekly timetable
    fetchWeeklyTimetableData(1, 1, today); // Default to 1st grade, 1st class, current week

    // Event listeners for grade, class, date, and next-week button
    const gradeSelect = document.getElementById('grade-select');
    const classSelect = document.getElementById('class-select');
    const fetchTimetableButton = document.getElementById('fetch-timetable-button');
    const nextWeekButton = document.getElementById('prev-week-button'); // ID remains prev-week-button for now

    if (fetchTimetableButton) {
        fetchTimetableButton.addEventListener('click', () => {
            const grade = gradeSelect.value;
            const classNumber = classSelect.value;
            const selectedDate = new Date(timetableDateInput.value);
            fetchWeeklyTimetableData(grade, classNumber, selectedDate);
        });
    }

    if (timetableDateInput) {
        timetableDateInput.addEventListener('change', () => {
            const grade = gradeSelect.value;
            const classNumber = classSelect.value;
            const selectedDate = new Date(timetableDateInput.value);
            fetchWeeklyTimetableData(grade, classNumber, selectedDate);
        });
    }

    // Change prev-week-button to next-week-button
    if (nextWeekButton) {
        nextWeekButton.id = 'next-week-button'; // Change ID
        nextWeekButton.textContent = '다음 주'; // Change text
        nextWeekButton.addEventListener('click', () => {
            const currentDate = new Date(timetableDateInput.value);
            currentDate.setDate(currentDate.getDate() + 7); // Go forward 7 days
            timetableDateInput.value = formatInputDate(currentDate);
            
            const grade = gradeSelect.value;
            const classNumber = classSelect.value;
            fetchWeeklyTimetableData(grade, classNumber, currentDate); // Fetch for the new week
        });
    }
});