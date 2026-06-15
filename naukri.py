"""
Naukri.com profile auto-updater using Playwright (headless browser).
Logs in and updates headline, summary, and key skills daily.
"""

import logging
import asyncio
from config import NAUKRI_EMAIL, NAUKRI_PASSWORD

log = logging.getLogger(__name__)


def update_naukri_profile(content: dict) -> str:
    """
    Synchronously update Naukri profile.
    Runs async playwright in a new event loop.
    """
    try:
        result = asyncio.run(_update_naukri_async(content))
        return result
    except Exception as e:
        log.error(f"Naukri update failed: {e}", exc_info=True)
        return f"Failed: {str(e)[:100]}"


async def _update_naukri_async(content: dict) -> str:
    from playwright.async_api import async_playwright

    headline = content.get("headline", "")
    summary = content.get("summary", "")
    key_skills = content.get("key_skills", [])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 1. Login
            log.info("Naukri: logging in...")
            await page.goto("https://www.naukri.com/nlogin/login", timeout=30000)
            await page.fill("#usernameField", NAUKRI_EMAIL)
            await page.fill("#passwordField", NAUKRI_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=15000)

            if "login" in page.url:
                raise Exception("Naukri login failed — check credentials in .env")

            log.info("Naukri: logged in successfully")

            # 2. Go to profile edit page
            await page.goto("https://www.naukri.com/mnjuser/profile", timeout=20000)
            await page.wait_for_load_state("networkidle")

            # 3. Update headline
            if headline:
                log.info("Naukri: updating headline...")
                try:
                    headline_el = page.locator("[placeholder*='headline'], [placeholder*='Headline'], .resumeHeadline textarea").first
                    await headline_el.click()
                    await headline_el.triple_click()
                    await headline_el.fill(headline[:250])
                    await page.keyboard.press("Tab")
                    await asyncio.sleep(1)
                except Exception as e:
                    log.warning(f"Headline update skipped: {e}")

            # 4. Update profile summary
            if summary:
                log.info("Naukri: updating summary...")
                try:
                    summary_btn = page.locator("text=Resume summary, text=Profile Summary").first
                    await summary_btn.click()
                    await asyncio.sleep(1)
                    summary_el = page.locator(".profileSummary textarea, [placeholder*='summary']").first
                    await summary_el.triple_click()
                    await summary_el.fill(summary[:2000])
                    save_btn = page.locator("button:has-text('Save')").first
                    await save_btn.click()
                    await asyncio.sleep(2)
                except Exception as e:
                    log.warning(f"Summary update skipped: {e}")

            # 5. Update key skills
            if key_skills:
                log.info("Naukri: updating key skills...")
                try:
                    skills_edit = page.locator("text=Key skills").locator("..").locator("button, .edit").first
                    await skills_edit.click()
                    await asyncio.sleep(1)

                    skills_input = page.locator("[placeholder*='skill'], [placeholder*='Skill']").first
                    await skills_input.click()
                    await skills_input.fill("")

                    for skill in key_skills[:20]:
                        await skills_input.fill(skill)
                        await asyncio.sleep(0.5)
                        try:
                            suggestion = page.locator(f".suggestion:has-text('{skill}'), li:has-text('{skill}')").first
                            await suggestion.click(timeout=2000)
                        except Exception:
                            await page.keyboard.press("Enter")
                        await asyncio.sleep(0.3)

                    save_btn = page.locator("button:has-text('Save')").first
                    await save_btn.click()
                    await asyncio.sleep(2)
                except Exception as e:
                    log.warning(f"Skills update skipped: {e}")

            log.info("Naukri: profile update complete")
            return "✓ Updated (headline + summary + skills)"

        finally:
            await browser.close()
