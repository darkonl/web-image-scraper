import os
from os import listdir
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import requests
import io
from PIL import Image
import time
import csv
import re
import pickle


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(ROOT_DIR, "imgs")


def flatten(x):
    result = []
    for el in x:
        if hasattr(el, "__iter__") and not isinstance(el, str):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result


def get_images_from_url(wd: webdriver, url: str, delay: int = 1):
    def scroll_down(wd: webdriver):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)

    print(f"INFO - Loading {url}")

    wd.get(url)

    image_urls = set()

    try:
        myElem = WebDriverWait(wd, 6).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted')
            )
        )
        print("Page is ready!")
    except TimeoutException:
        print(f"Loading {url} took too much time!")
        return image_urls

    try:
        first_image = wd.find_element(By.CSS_SELECTOR, "div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted")
        first_image.click()
    except Exception as e:
        print(f"FAILED - Loading {url} - {e}")
        return image_urls

    max_images = 1

    while len(image_urls) < max_images:
        try:
            # first, set the number of images in current window
            if max_images == 1:
                number_of_images = WebDriverWait(wd, 20).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         """//*[@id="ui-tabpanel-0"]/div[1]/div[2]/div/ngx-gallery/div/ngx-gallery-preview/div[3]/div[2]""")
                    )
                )
                if number_of_images.get_attribute('textContent'):
                    max_images = int(re.sub(r".*\/\s*(.*)", r"\1", number_of_images.get_attribute('textContent')))

            # retrieve image url source
            img_src = wd.find_element(By.CLASS_NAME, "ngx-gallery-preview-img")
            if img_src.get_attribute('src') and 'http' in img_src.get_attribute('src') and not img_src.get_attribute('src') in image_urls:
                image_urls.add(img_src.get_attribute('src'))
                print(f"Loaded {len(image_urls)}/{max_images}")

            # navigate to next image
            clickable_element = WebDriverWait(wd, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH,"""//*[@id="ui-tabpanel-0"]/div[1]/div[2]/div/ngx-gallery/div/ngx-gallery-preview/ngx-gallery-arrows/div[2]/div""")
                )
            )

            clickable_element.click()
        except Exception as e:
            print(f"FAILED - {e}")
            continue

    return image_urls


def download_image(download_path: str, url: str, file_name: str):
    try:
        image_content = requests.get(url).content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file)
        file_path = download_path + file_name  # use os.path.join instead

        with open(file_path, 'wb') as f:
            image.save(f, "JPEG")

        print("Success")
    except Exception as e:
        print('FAILED - ', e)


def save_urls():
    csv_path = os.path.join(ROOT_DIR, "cerca.csv")
    with open(csv_path, encoding='cp850') as f:
        reader = csv.reader(f)
        data = list(reader)
    data = flatten(data)
    urls_list = list(filter(lambda x: "http" in x, data))
    urls_list = [re.search("(?P<url>https?://\\S+)", x).group("url") for x in urls_list]

    with open(f'urls/arxiusenlinia_urls.pkl', 'wb') as f:
        pickle.dump({"urls": urls_list}, f)


def scrap_images_from_csv(url: str = None):
    with open('urls/arxiusenlinia_urls.pkl', 'rb') as f:
        url_dict = pickle.load(f)

    files_path = os.path.join(ROOT_DIR, "urls")
    files_indices = [int(re.search(r'(\d+)', str(f.name)).group(1)) for f in os.scandir(files_path) if f.is_file() and any(char.isdigit() for char in f.name)]
    for i in range(max(files_indices), len(url_dict["urls"])):
        print(f"""INFO - Reading file {i}/{len(url_dict["urls"])}""")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        img_urls = get_images_from_url(wd=driver, url=url_dict["urls"][i], delay=1)
        img_urls_dict = {url: img_urls}
        with open(f'urls/url-{i}.pkl', 'wb') as f:
            pickle.dump(img_urls_dict, f)
        driver.quit()


def download_imgs():
    files_dir = os.path.join(ROOT_DIR, "urls")
    files_path = [f for f in os.scandir(files_dir) if f.is_file() and any(char.isdigit() for char in f.name)]
    output_img_path = os.path.join(ROOT_DIR, "imgs")
    file_index = 0
    for path in files_path:
        with open(path, 'rb') as f:
            imgs_dict = pickle.load(f)
        for key in imgs_dict:
            img_srcs = imgs_dict[key]
            for img in img_srcs:
                img_data = requests.get(img).content
                with open(os.path.join(output_img_path, f"img_{file_index}.jpeg"), 'wb') as handler:
                    handler.write(img_data)
                file_index += 1


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    download_imgs()


