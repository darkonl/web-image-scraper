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
import csv
import re
import pickle
import tkinter as tk
from tkinter import filedialog as fd
import logging

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

    try:
        myElem = WebDriverWait(wd, 6).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted')
            )
        )
        logging.debug("Page is ready!")
    except TimeoutException:
        logging.error(f"Loading {url} took too much time!")
        return image_urls
    except Exception as e:
        logging.error(f"Something went wrong with {url}")
        logging.error(f"Message: {str(e)}")
        return image_urls


    try:
        first_image = wd.find_element(By.CSS_SELECTOR, "div.ngx-gallery-image.ngx-gallery-active.ngx-gallery-clickable.ng-star-inserted")
        first_image.click()
    except Exception as e:
        logging.error(f"Something went wrong with {url}")
        logging.error(f"Message: {str(e)}")
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
                logging.debug(f"Loaded {len(image_urls)}/{max_images}")

            # navigate to next image
            clickable_element = WebDriverWait(wd, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH,"""//*[@id="ui-tabpanel-0"]/div[1]/div[2]/div/ngx-gallery/div/ngx-gallery-preview/ngx-gallery-arrows/div[2]/div""")
                )
            )

            clickable_element.click()
        except Exception as e:
            logging.error(f"Something went wrong on retrieving image urls")
            logging.error(f"Message: {str(e)}")
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


def get_last_file_read() -> dict:
    dict_files = [os.path.basename(f).split('.')[0] for f in os.listdir(HISTORY_PATH) if f.endswith(".pkl")]
    dict_files = [re.sub(r"dict-(.*)", r"\1", line) for line in dict_files]
    dict_files = [datetime.datetime.strptime(date_string, DATE_TIME_FORMAT) for date_string in dict_files]
    dict_files.sort()
    last_date = dict_files[-1]
    dict_files = [f for f in os.listdir(HISTORY_PATH) if last_date.strftime(DATE_TIME_FORMAT) in f]
    if len(dict_files) != 1:
        raise Exception(f"It should be only 1 file with date_time = {last_date}")

    with open(os.path.join(HISTORY_PATH, dict_files[0]), 'rb') as f:
        last_dict = pickle.load(f)
    for key in last_dict:
        print(f"{key}: {last_dict[key]}")
    print(last_dict)


def scrap_images_from_txt(filename: str = None, continue_last_job: bool = False):
    """Scans images in URLs prodivded in the .txt file"""
    assert filename
    logging.debug(f"Reading file {filename}...")
    try:
        # first: create needed folders
        if not URLS_PATH:
            # create urls folder if does not exist to store urls files with images' urls
            os.makedirs(URLS_PATH)
        if not HISTORY_PATH:
            # create 'history' folder if does not exist to store last tries fetching images' urls
            os.makedirs(HISTORY_PATH)

        # load text file -> lines to list of strings (one item for each url)
        with open(filename, encoding="utf-8") as file:
            # urls in filename to list
            lines = file.read().splitlines()
        # create dictionary for history tracking
        url_img_count_dict = {}
        if LOAD_LAST_JOB:
            url_img_count_dict = get_last_file_read()
        # initialize driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        for line in lines:
            code = re.sub(r".*\/(.*)", r"\1", line)
            logging.debug(f"Step: {code} ({lines.index(line) + 1}/({len(lines)}))")
            images = ["url1", "url2"]  # get_images_from_url(wd=driver, url=line, )
            url_img_count_dict[code] = len(images)

            output_file = os.path.join(ROOT_DIR, "urls", f"{code}.txt")
            with open(output_file, 'w+') as f:
                f.write('\n'.join(images))
        driver.quit()
        # save dictionary for traceability
        with open(os.path.join(HISTORY_PATH, f"dict-{time.strftime(DATE_TIME_FORMAT)}.pkl"), 'w+') as f:
            pickle.dump(url_img_count_dict, f)

    except Exception as e:
        logging.error(f"Failed to read file {filename}...")
        logging.error(f"Message: {str(e)}")
        return

    logging.debug(f"Successfully read {filename}!")
    logging.debug(f"Txt files saved in the /urls folder for each result (total={len(lines)} files)")



class App(tk.Tk):
    file_name = None
    load_last_file = False

    def set_file_name(self):
        self.file_name = fd.askopenfilename(
            title="Select .txt file",
            filetypes=[("Text files", ".txt")]
        )

    def set_run_last_job(self):
        self.load_last_file = not self.load_last_file

    def start_application(self):
        scrap_images_from_txt(self.file_name, self.load_last_file)

    def __init__(self, file_name: str = None, load_last_file: bool = False):
        super().__init__()
        self.file_name = file_name
        self.load_last_file = load_last_file
        self.title("Web image scraper")
        self.geometry("300x300")
        self.chk_last_job = tk.Checkbutton(self, text='Continue last job', onvalue=True, offvalue=False, command=self.set_run_last_job)
        self.chk_last_job.place(x=50, y=20)
        self.chk_last_job.pack()

        self.set_file_button = tk.Button(self, text="Choose text file", command=self.set_file_name)
        self.set_file_button.place(x=50, y=80)
        self.set_file_button.pack()

        self.start_button = tk.Button(self, text="START", command=self.start_application)
        self.start_button.place(x=50, y=140)
        self.start_button.pack()


if __name__ == "__main__":
    app = App()
    app.mainloop()


