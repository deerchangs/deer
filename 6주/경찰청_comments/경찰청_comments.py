import multiprocessing
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# CSV 파일 경로
file_path = 'collected_data_20240628_024809.csv'

# CSV 파일 불러오기
df_collected_links = pd.read_csv(file_path)

df_filtered = df_collected_links

# 셀레니움 옵션 설정
chrome_options = Options()
#chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-browser-side-navigation")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

# 댓글 수집 함수 정의
def collect_comments(driver, index, row, filename, total_count):
    original_link = row['Link']
    modified_link = original_link.replace("/article/", "/article/comment/")
    print(f"Thread {index + 1}/{total_count} accessing: {modified_link}")
    
    driver.get(modified_link)
    
    comments_data = []

    # "더보기" 버튼 클릭을 통한 댓글 로딩
    while True:
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".u_cbox_btn_more"))
            )
            more_button.click()
            time.sleep(0.5)
        except (NoSuchElementException, TimeoutException):
            break

    # 데이터 수집
    while True:
        try:
            comments = driver.find_elements(By.CSS_SELECTOR, ".u_cbox_contents")
            comment_dates = driver.find_elements(By.CSS_SELECTOR, ".u_cbox_date")
            recommend_counts = driver.find_elements(By.CSS_SELECTOR, ".u_cbox_cnt_recomm")
            unrecommend_counts = driver.find_elements(By.CSS_SELECTOR, ".u_cbox_cnt_unrecomm")
            break
        except StaleElementReferenceException:
            time.sleep(0.5)

    for i in range(len(comments)):
        try:
            comment = comments[i].text
            comment_date = comment_dates[i].text
            recommend_count = recommend_counts[i].text
            unrecommend_count = unrecommend_counts[i].text

            comments_data.append({
                "Accessed URL": modified_link,
                "Comment": comment,
                "Comment Date": comment_date,
                "Recommend Count": recommend_count,
                "Unrecommend Count": unrecommend_count
            })
        except StaleElementReferenceException:
            continue
    
    print(f"Thread {index + 1}/{total_count} completed: {modified_link}")

    # 수집된 데이터를 실시간으로 CSV 파일에 저장
    df = pd.DataFrame(comments_data)
    df.to_csv(filename, mode='a', index=False, header=False, encoding='utf-8-sig')
    
    return comments_data

def initialize_driver():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

if __name__ == "__main__":
    num_threads = 1  # 동시에 실행할 스레드 수를 지정

    # 실시간 저장을 위한 파일명 설정
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'collected_comments_{current_time}.csv'

    # CSV 파일에 헤더를 먼저 저장
    df = pd.DataFrame(columns=["Accessed URL", "Comment", "Comment Date", "Recommend Count", "Unrecommend Count"])
    df.to_csv(filename, mode='w', index=False, encoding='utf-8-sig')

    # 전체 링크 개수 계산
    total_count = len(df_filtered)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        drivers = [initialize_driver() for _ in range(num_threads)]
        futures = []
        for index, row in df_filtered.iterrows():
            driver = drivers[index % num_threads]  # 스레드에 따라 드라이버를 재사용
            futures.append(executor.submit(collect_comments, driver, index, row, filename, total_count))
        
        # 모든 작업이 완료될 때까지 기다림
        for future in futures:
            future.result()
        
        # 모든 작업이 완료된 후 드라이버 종료
        for driver in drivers:
            driver.quit()

    print(f"Data collection for specified date range completed and saved to '{filename}'.")
