from DrissionPage import ChromiumPage 
from RecaptchaSolver import RecaptchaSolver
import time

def main():
    driver = ChromiumPage()
    recaptchaSolver = RecaptchaSolver(driver)
    driver.get("https://lattes.cnpq.br/0717252455115225")#https://www.google.com/recaptcha/api2/demo
    # Attempt to solve using a forced iframe index that matches this page's
    # challenge frame (observed to be index 3 in local debugging). If this
    # fails, the solver will fall back to automatic detection.
    recaptchaSolver.solveCaptcha(preferred_iframe_index=3)

    # After solving the captcha, submit the form if a submit button exists on the page.
    try:
        # try common submit selectors
        try:
            btn = driver.ele("button[type=submit]", timeout=1)
            btn.click()
            print("[main] clicked button[type=submit]")
        except Exception as e:
            print(f"[main] button[type=submit] error: {e}")
            try:
                btn = driver.ele("input[type=submit]", timeout=1)
                btn.click()
                print("[main] clicked input[type=submit]")
            except Exception as e:
                print(f"[main] input[type=submit] error: {e}")
                # try to find a button with visible text 'Submeter' (Portuguese)
                try:
                    btn = driver("xpath://button[contains(normalize-space(.), 'Submeter')]")
                    btn.click()
                    print("[main] clicked button with text 'Submeter'")
                except Exception as e:
                    print(f"[main] xpath button Submeter error: {e}")
                    # minimal page-specific fallbacks (observed on CNPq)
                    try:
                        btn = driver.ele("#submitBtn", timeout=1)
                        btn.click()
                        print("[main] clicked #submitBtn")
                    except Exception as e:
                        print(f"[main] #submitBtn error: {e}")
                        try:
                            btn = driver.ele("xpath://input[@value='Submeter']", timeout=1)
                            btn.click()
                            print("[main] clicked input[value='Submeter']")
                        except Exception as e:
                            print(f"[main] input[value=Submeter] error: {e}")
                            print("[main] no submit button found or clickable; skipping submit step")
    except Exception as e:
        print(f"[main] error while attempting to submit form: {e}")

    # short delay then save the page HTML for debugging / record
    try:
        # give more time for navigation/processing to finish
        time.sleep(5)
        html = None
        try:
            html = driver.execute_script("return document.documentElement.outerHTML;")
        except Exception:
            # fallback: some wrappers expose page_source
            html = getattr(driver, 'page_source', None)
        # Try to capture MHTML via CDP if available (preferred single-file snapshot)
        mhtml_saved = False
        try:
            cdp_callers = [
                getattr(driver, 'execute_cdp_cmd', None),
                getattr(getattr(driver, 'driver', None), 'execute_cdp_cmd', None),
                getattr(getattr(driver, 'browser', None), 'execute_cdp_cmd', None),
            ]
            for cdp in cdp_callers:
                if callable(cdp):
                    try:
                        res = cdp("Page.captureSnapshot", {"format": "mhtml"})
                        data = None
                        if isinstance(res, dict) and 'data' in res:
                            data = res['data']
                        elif isinstance(res, str):
                            data = res
                        if data:
                            with open('saved_after_submit.mhtml', 'wb') as f:
                                f.write(data.encode('utf-8'))
                            print('[main] saved saved_after_submit.mhtml')
                            mhtml_saved = True
                            break
                    except Exception as e:
                        print(f"[main] cdp Page.captureSnapshot attempt error: {e}")
                        continue
        except Exception:
            pass

        if not mhtml_saved:
            if html:
                with open('saved_after_submit.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print('[main] saved saved_after_submit.html')
            else:
                print('[main] no page HTML available to save')
    except Exception as e:
        print(f"[main] error while saving page HTML: {e}")

    return 0


if __name__ == "__main__":
    main()
