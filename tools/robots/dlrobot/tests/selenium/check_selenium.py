import os
import logging
import sys
sys.path.append('../../../common')
from selenium_driver import TSeleniumDriver

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



if __name__ == "__main__":
    logger = logging.getLogger("dlrobot_logger")
    setup_logging(logger, "check_selenium.log")

    try:
        driver_holder = TSeleniumDriver()
        driver_holder.start_executable()
    except Exception as exp:
        print(exp)
        sys.exit(1)

    #mid.ru is a wholly javascripted website
    links = driver_holder.navigate_and_get_links(sys.argv[1])

    logger.info("Title:{}, type={}\n".format(driver_holder.the_driver.title, type(driver_holder.the_driver.title)))
    print ("html len: {0}".format(len(driver_holder.the_driver.page_source)))
    assert len(links) > 0
    print ("links and buttons found: {0}".format(len(links)))
    for e in links:
        try:
            if e.text is None:
                continue
            link_text = e.text.strip('\n\r\t ')
            if link_text.lower().startswith(sys.argv[2]):
                driver_holder.click_element(e)
                print(driver_holder.the_driver.current_url)
                assert driver_holder.the_driver.current_url == sys.argv[3]
                break
        except Exception as exp:
            print (exp)
    driver_holder.stop_executable()