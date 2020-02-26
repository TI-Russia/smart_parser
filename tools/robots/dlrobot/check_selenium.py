from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import os
import time
import logging
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def setup_logging( logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def click_element(driver, element):
    logger = logging.getLogger("my_logger")
    print("click element with text {}".format(element.text.strip('\n\r\t ')))
    #driver.execute_script('window.scrollTo(0,{});'.format(element.location['y']))
    driver.execute_script("arguments[0].scrollIntoView({block: \"center\", behavior: \"smooth\"});", element)
    #element.click()
    #element.scrollIntoView()
    # open in a new tab, send ctrl-click
    window_before = driver.window_handles[0]

    ActionChains(driver) \
        .key_down(Keys.CONTROL) \
        .click(element) \
        .key_up(Keys.CONTROL) \
        .perform()

    time.sleep(6)
    if len(driver.window_handles) < 2:
        logger.debug("cannot click, no new window is found")
        return
    window_after = driver.window_handles[1]
    driver.switch_to.window(window_after)


logger = logging.getLogger("my_logger")
setup_logging(logger, "check_selenium.log")

options = FirefoxOptions()
options.headless = True
driver = webdriver.Firefox(options=options)
#driver.get("http://www.ya.ru")
#driver.get("http://oblsud.tula.sudrf.ru") # windows-1251
driver.get("http://www.mkrf.ru/about/territorial_authorities/upravlenie_ministerstva_kultury_rossiyskoy_federatsii_po_tsentralnomu_federalnomu_okrugu_/anti-corruption/")



logger.info("Title:{}, type={}\n".format(driver.title, type(driver.title)))

print ("html len: {0}".format(len(driver.page_source)))
elements = list(driver.find_elements_by_xpath('//button | //a'))
#for index, e in enumerate(elements):
#    print ("{} {}".format(index, e.text.strip('\n\r\t ')))
print ("links and buttons found: {0}".format(len(elements)))
#popup = driver.find_element_by_xpath('//div[contains(@class,"ui-dialog") and @aria-describedby="dialogContent2"]//button[@title="Close"]')
#if popup is not None:
#    popup.click()
element = elements[368]
href = element.get_attribute("href")
click_element(driver, elements[368])

print ("url after click")
print (driver.current_url)
assert driver.current_url == "http://www.mkrf.ru/about/territorial_authorities/upravlenie_ministerstva_kultury_rossiyskoy_federatsii_po_tsentralnomu_federalnomu_okrugu_/anti-corruption/"
driver.quit()