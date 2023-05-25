import os
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
import datetime
import re
import pickle
import tkinter as tk
from tkinter import filedialog as fd
import logging
import sys
import threading
from pathlib import Path

IS_DEBUG = False if sys.gettrace() is None else True

logging.basicConfig(
    filename='app.log',
    filemode='w',
    format='%(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(ROOT_DIR, "imgs")
HISTORY_PATH = os.path.join(ROOT_DIR, "history")
URLS_PATH = os.path.join(ROOT_DIR, "urls")
DATE_TIME_FORMAT = '%Y%m%d-%H%M%S'
LOAD_LAST_JOB = False
URL_FILE_NAME = None
IMGS_PATH = os.path.join(ROOT_DIR, "imgs")


def flatten(x):
    result = []
    for el in x:
        if hasattr(el, "__iter__") and not isinstance(el, str):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result


def get_images_from_url(wd: webdriver, url: str, delay: int = 1) -> set():
    """It retrieves all image urls inside the url sent"""
    def scroll_down(wd: wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)

    logging.debug(f"Loading {url}...")

    wd.get(url)

    image_urls = set()

    max_images = 1

    try:
        myElem = WebDriverWait(wd, 6).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted')
            )
        )
        logging.debug("Page is ready!")
    except TimeoutException:
        logging.error(f"Loading {url} took too much time!")
        return image_urls, max_images
    except Exception as e:
        logging.error(f"Something went wrong with {url}")
        logging.error(f"Message: {str(e)}")
        return image_urls, max_images


    try:
        first_image = wd.find_element(By.CSS_SELECTOR, "div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted")
        first_image.click()
    except Exception as e:
        logging.error(f"Something went wrong with {url}")
        logging.error(f"Message: {str(e)}")
        return image_urls, max_images

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
                logging.debug(f"Loaded {len(image_urls)}/{max_images}")

            # navigate to next image
            clickable_element = WebDriverWait(wd, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH,"""//*[@id="ui-tabpanel-0"]/div[1]/div[2]/div/ngx-gallery/div/ngx-gallery-preview/ngx-gallery-arrows/div[2]/div""")
                )
            )

            if IS_DEBUG and len(image_urls) > 5:
                return image_urls, max_images

            clickable_element.click()
        except Exception as e:
            logging.error(f"Something went wrong on retrieving image urls")
            logging.error(f"Message: {str(e)}")
            continue

    return image_urls, max_images


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


def ensure_dir_created(path: str = None):
    assert path
    if not os.path.exists(path):
        # create urls folder if does not exist to store urls files with images' urls
        os.makedirs(path)


def download_imgs():
    # first: create needed folders
    ensure_dir_created(IMGS_PATH)

    files_path = [os.path.join(URLS_PATH, f) for f in os.listdir(URLS_PATH) if f.endswith(".txt")]
    file_index = 0
    for path in files_path:
        try:
            logging.debug(f"Downloading images from {path}")

            code = Path(path).stem
            img_url_list = []
            with open(path, 'r', encoding='UTF-8') as f:
                while line := f.readline():
                    img_url_list.append(line.rstrip())
            for img_url in img_url_list:
                img_data = requests.get(img_url).content
                img_name = Path(img_url).stem
                ensure_dir_created(os.path.join(IMGS_PATH, code))
                with open(os.path.join(IMGS_PATH, code, f"{img_name.replace(',', '_')}.jpg"), 'wb') as handler:
                    handler.write(img_data)
                file_index += 1
            logging.debug(f"Successfully saved {len(img_url_list)} in {os.path.join(IMGS_PATH, code)}")
        except Exception as e:
            logging.error(f"Failed to read {path}")
            logging.error(f"Message: {str(e)}")


def get_last_file_read() -> dict:
    dict_files = [os.path.basename(f).split('.')[0] for f in os.listdir(HISTORY_PATH) if f.endswith(".pkl")]
    dict_files = [re.sub(r"dict-(.*)", r"\1", line) for line in dict_files]
    dict_files = [datetime.datetime.strptime(date_string, DATE_TIME_FORMAT) for date_string in dict_files]
    if len(dict_files) == 0:
        return dict()
    dict_files.sort()
    last_date = dict_files[-1]
    dict_files = [f for f in os.listdir(HISTORY_PATH) if last_date.strftime(DATE_TIME_FORMAT) in f]
    if len(dict_files) != 1:
        raise Exception(f"There should be only 1 file with date_time = {last_date}")

    with open(os.path.join(HISTORY_PATH, dict_files[0]), 'rb') as f:
        last_dict = pickle.load(f)

    assert last_dict

    return last_dict


def run_url(line: str, url_img_count_dict: dict) -> bool:
    for key in url_img_count_dict:
        if key in line:
            text_file_read = [f for f in os.listdir(URLS_PATH) if f.endswith(".txt") and key in f]
            if len(text_file_read) == 0:
                return True
            if len(text_file_read) > 1:
                raise Exception(f"There should be at least one file containing {key}")
            file_path = os.path.join(URLS_PATH, text_file_read[0])
            with open(file_path, 'r') as fp:
                for count, line in enumerate(fp):
                    pass
            if count + 1 is url_img_count_dict[key]:
                return False
            return True
    return True


def scrap_images_from_txt(filename: str = None, continue_last_job: bool = False):
    """Scans images in URLs prodivded in the .txt file"""
    assert filename
    logging.debug(f"Reading file {filename}...")
    count = 0
    try:
        # first: create needed folders
        if not os.path.exists(URLS_PATH):
            # create urls folder if does not exist to store urls files with images' urls
            os.makedirs(URLS_PATH)
        if not os.path.exists(HISTORY_PATH):
            # create 'history' folder if does not exist to store last tries fetching images' urls
            os.makedirs(HISTORY_PATH)

        # load text file -> lines to list of strings (one item for each url)
        with open(filename, encoding="utf-8") as file:
            # urls in filename to list
            lines = file.read().splitlines()

        # create dictionary for history tracking
        url_img_count_dict = {}
        if continue_last_job:
            url_img_count_dict = get_last_file_read()

        for line in lines:
            if continue_last_job and not run_url(line, url_img_count_dict):
                continue

            code = re.sub(r".*\/(.*)", r"\1", line)
            logging.info(f"Reading {code}...")

            # create new driver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

            logging.debug(f"Step: {code} ({lines.index(line) + 1}/({len(lines)}))")
            images, image_count = get_images_from_url(wd=driver, url=line, )
            logging.info(f"Successfully read {code}, fetched a total of {image_count} images (url: {line})")
            url_img_count_dict[code] = image_count

            output_file = os.path.join(ROOT_DIR, "urls", f"{code}.txt")
            with open(output_file, 'w+') as f:
                f.write('\n'.join(images))

            # dispose driver
            driver.quit()
            count += 1
            if IS_DEBUG and count == 10:
                break
        # save dictionary for traceability
        if len(url_img_count_dict) != 0:
            with open(os.path.join(HISTORY_PATH, f"dict-{time.strftime(DATE_TIME_FORMAT)}.pkl"), 'wb+') as f:
                pickle.dump(url_img_count_dict, f)

    except Exception as e:
        logging.error(f"Failed to read file {filename}...")
        logging.error(f"Message: {str(e)}")

        if len(url_img_count_dict) != 0:
            with open(os.path.join(HISTORY_PATH, f"dict-{time.strftime(DATE_TIME_FORMAT)}.pkl"), 'wb+') as f:
                pickle.dump(url_img_count_dict, f)
        return

    logging.debug(f"Successfully read {filename}!")
    logging.debug(f"Txt files saved in the /urls folder for each result (total={len(lines)} files)")


class App(tk.Tk):
    file_name = None
    load_last_file = False

    def refresh(self):
        self.update()
        self.after(1000, self.refresh)

    def set_file_name(self):
        self.file_name = fd.askopenfilename(
            title="Select .txt file",
            filetypes=[("Text files", ".txt")]
        )

    def set_run_last_job(self):
        self.load_last_file = not self.load_last_file

    def start_application(self):
        scrap_images_from_txt(self.file_name, self.load_last_file)

    def start_download(self):
        self.refresh()
        threading.Thread(target=download_imgs).start()

    def __init__(self, file_name: str = None, load_last_file: bool = False):
        super().__init__()
        self.file_name = file_name
        self.load_last_file = load_last_file
        self.title("Web image scraper")
        self.geometry("300x300")
        self.chk_last_job = tk.Checkbutton(self,
                                           text='Continue last job',
                                           onvalue=True,
                                           offvalue=False,
                                           command=self.set_run_last_job)
        self.chk_last_job.place(x=50, y=20)
        self.chk_last_job.pack()

        self.set_file_button = tk.Button(self, text="Choose text file", command=self.set_file_name)
        self.set_file_button.place(x=50, y=80)
        self.set_file_button.pack()

        self.start_button = tk.Button(self, text="START", command=self.start_application)
        self.start_button.place(x=50, y=140)
        self.start_button.pack()

        self.start_button = tk.Button(self, text="DOWNLOAD", command=self.start_download)
        self.start_button.place(x=50, y=200)
        self.start_button.pack()


if __name__ == "__main__":
    app = App()
    app.mainloop()


