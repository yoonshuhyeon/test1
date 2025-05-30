import requests

# API URL (실제 URL로 변경)
api_url = "https://open.neis.go.kr/hub/mealServiceDietInfo?KEY=368ccd7447b04140b197c937a072fb76&Type=json&ATPT_OFCDC_SC_CODE=T10&SD_SCHUL_CODE=9290055&MLSV_YMD=20250522"

response = requests.get(api_url)
data = response.json()

# 급식 정보가 있는 부분으로 경로 탐색 (예: data['mealServiceDietInfo'][1]['row'])
meal_rows = data.get('mealServiceDietInfo', [])[1].get('row', [])

for meal in meal_rows:
    print(f"식사코드: {meal.get('MMEAL_SC_CODE')}")
    print(f"식사명: {meal.get('MMEAL_SC_NM')}")
    print(f"급식일자: {meal.get('MLSV_YMD')}")
    print(f"급식인원수: {meal.get('MLSV_FGR')}")
    print(f"요리명: {meal.get('DDISH_NM')}")
    print(f"원산지정보: {meal.get('ORPLC_INFO')}")
    print(f"칼로리정보: {meal.get('CAL_INFO')}")
    print(f"영양정보: {meal.get('NTR_INFO')}")
    print(f"급식시작일자: {meal.get('MLSV_FROM_YMD')}")
    print(f"급식종료일자: {meal.get('MLSV_TO_YMD')}")
    print(f"수정일자: {meal.get('LOAD_DTM')}")
    print("------------------------------------------------")
