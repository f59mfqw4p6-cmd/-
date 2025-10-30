# app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import random
import pandas as pd

st.set_page_config(page_title="로또 번호 추첨기", layout="centered")

st.title("로또 번호 추첨기 (6/45) 🎯")
st.write("1부터 45까지 중에서 6개 숫자를 추천해 줍니다. 최근 당첨번호를 불러와 만든 번호와 비교합니다.")

# 사이드바: 몇 세트 생성할지
sets = st.sidebar.number_input("생성할 세트 수", min_value=1, max_value=20, value=5, step=1)
sort_each = st.sidebar.checkbox("각 세트 내 번호 정렬", value=True)
st.sidebar.write("---")
st.sidebar.write("참고: 최신 회차는 동행복권 홈페이지에서 자동으로 확인합니다.")

# 함수: 최신 회차 번호(회차 숫자)를 가져오기 (웹페이지 파싱)
def get_latest_draw_no():
    try:
        url = "https://www.dhlottery.co.kr/"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # 메인 페이지의 최신 회차가 들어있는 element: <strong id="lottoDrwNo">XXXX</strong>
        el = soup.find("strong", {"id": "lottoDrwNo"})
        if el and el.text.strip().isdigit():
            return int(el.text.strip())
    except Exception:
        return None

# 함수: 특정 회차의 당첨번호 JSON 가져오기 (동행복권 내부 API)
def fetch_draw_numbers(drw_no):
    try:
        api = "https://www.dhlottery.co.kr/common.do"
        params = {"method": "getLottoNumber", "drwNo": drw_no}
        r = requests.get(api, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("returnValue") == "success":
            nums = [data.get(f"drwtNo{i}") for i in range(1,7)]
            bonus = data.get("bnusNo")
            date = data.get("drwNoDate")
            return {"drwNo": data.get("drwNo"), "date": date, "numbers": nums, "bonus": bonus}
    except Exception:
        return None

# 함수: 로또 세트 생성
def generate_sets(n_sets, sort_each=True):
    results = []
    for i in range(n_sets):
        s = random.sample(range(1,46), 6)
        if sort_each:
            s.sort()
        results.append(s)
    return results

# 숫자 생성 버튼
if st.button("생성하기"):
    with st.spinner("번호 생성 중..."):
        generated = generate_sets(sets, sort_each=sort_each)
        df = pd.DataFrame({
            "세트": [f"세트 {i+1}" for i in range(len(generated))],
            "번호": [", ".join(f"{x:02d}" for x in g) for g in generated]
        })
        st.success(f"{len(generated)}개 세트 생성 완료!")
        st.dataframe(df, use_container_width=True)

        # 최신 회차 자동 가져오기
        st.markdown("### 최근 당첨번호 가져오기 및 비교")
        latest_no = get_latest_draw_no()
        if latest_no is None:
            st.warning("동행복권 메인페이지에서 최신 회차를 확인하지 못했습니다. 회차 번호를 수동으로 입력하세요.")
            manual = st.number_input("회차 입력 (예: 1195)", min_value=1, value=latest_no or 1, step=1)
            draw_info = fetch_draw_numbers(manual)
        else:
            st.info(f"가장 최신 회차로 시도합니다: {latest_no}회")
            draw_info = fetch_draw_numbers(latest_no)
            if draw_info is None:
                st.warning("API로 당첨번호를 불러오지 못했습니다. 회차를 수동 입력해보세요.")
                manual = st.number_input("회차 입력 (예: 1195)", min_value=1, value=latest_no, step=1)
                draw_info = fetch_draw_numbers(manual)

        if draw_info:
            win_nums = set(draw_info["numbers"])
            bonus = draw_info["bonus"]
            st.write(f"**회차 {draw_info['drwNo']}**  추첨일: {draw_info['date']}")
            st.write("당첨번호: " + ", ".join(f"{n:02d}" for n in draw_info["numbers"]) + f"  + 보너스 {bonus:02d}")

            # 비교: 각 세트와 당첨번호 비교
            compare_rows = []
            for i, g in enumerate(generated):
                gset = set(g)
                match = sorted(list(gset & win_nums))
                match_cnt = len(match)
                bonus_match = (bonus in gset)
                # 등수 판단 (간단)
                if match_cnt == 6:
                    rank = "1등"
                elif match_cnt == 5 and bonus_match:
                    rank = "2등"
                elif match_cnt == 5:
                    rank = "3등"
                elif match_cnt == 4:
                    rank = "4등"
                elif match_cnt == 3:
                    rank = "5등"
                else:
                    rank = "낙첨"
                compare_rows.append({
                    "세트": f"세트 {i+1}",
                    "번호": ", ".join(f"{x:02d}" for x in g),
                    "맞춘개수": match_cnt,
                    "맞춘번호": ", ".join(f"{x:02d}" for x in match) if match else "-",
                    "보너스포함": "예" if bonus_match else "아니오",
                    "결과": rank
                })
            comp_df = pd.DataFrame(compare_rows)
            st.table(comp_df)
        else:
            st.error("당첨정보를 불러오지 못했습니다. 인터넷 연결 또는 사이트 변경 여부를 확인하세요.")
