from DrissionPage import ChromiumPage 
from RecaptchaSolver import RecaptchaSolver

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
        except Exception:
            try:
                btn = driver.ele("input[type=submit]", timeout=1)
                btn.click()
                print("[main] clicked input[type=submit]")
            except Exception:
                # try to find a button with visible text 'Submeter' (Portuguese)
                try:
                    btn = driver("xpath://button[contains(normalize-space(.), 'Submeter')]")
                    btn.click()
                    print("[main] clicked button with text 'Submeter'")
                except Exception:
                    print("[main] no submit button found or clickable; skipping submit step")
    except Exception as e:
        print(f"[main] error while attempting to submit form: {e}")

    return 0


if __name__ == "__main__":
    main()
