from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions

options = FirefoxOptions()
options.headless = True
driver = webdriver.Firefox(options=options)
driver.get("http://www.ya.ru")
print ("html len: {0}".format(len(driver.page_source)))
driver.quit()