import time
import random
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from sqlalchemy.orm import sessionmaker
from flask import current_app
import re
from selenium.webdriver.common.action_chains import ActionChains
from ..ai.messaging import ai_generate_message, predict_best_variant
import spacy
nlp = spacy.load('en_core_web_sm')

COOKIES_FILE = 'linkedin_cookies.pkl'

class LinkedInScraper:
    def __init__(self, app, user_data_dir=None):
        self.app = app
        self.driver = None
        self._stop_flag = False
        # Use a persistent Chrome profile directory for session persistence
        if user_data_dir is None:
            self.user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chrome_profile'))
        else:
            self.user_data_dir = user_data_dir
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def stop(self):
        self._stop_flag = True
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def start_driver(self, headless=False):
        options = Options()
        # Use persistent user data dir for Chrome profile (keeps you logged in)
        if os.path.exists(os.path.join(self.user_data_dir, 'SingletonLock')):
            print('WARNING: Chrome profile is already in use by another process. Please close all Chrome windows using this profile before running the scraper.')
        options.add_argument(f'--user-data-dir={self.user_data_dir}')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--remote-debugging-port=9222')
        # Anti-bot options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        # Custom user-agent (imitate real Chrome)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
        # Remove detach by default for stability
        # If you want Chrome to stay open after script, set detach=True below
        # options.add_experimental_option('detach', True)
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=options)

    def save_cookies(self):
        with open(COOKIES_FILE, 'wb') as f:
            pickle.dump(self.driver.get_cookies(), f)

    def load_cookies(self):
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            return True
        return False

    def ensure_logged_in(self):
        self.driver.get('https://www.linkedin.com/')
        time.sleep(2)
        if self.is_logged_in():
            return True
        # Try loading cookies
        self.driver.delete_all_cookies()
        self.driver.get('https://www.linkedin.com/')
        if self.load_cookies():
            self.driver.refresh()
            time.sleep(2)
            if self.is_logged_in():
                return True
        # Prompt for manual login
        print('Please log in to LinkedIn in the opened browser window.')
        while not self.is_logged_in():
            time.sleep(5)
        self.save_cookies()
        print('Login detected and cookies saved.')
        return True

    def is_logged_in(self):
        try:
            self.driver.get('https://www.linkedin.com/feed/')
            time.sleep(2)
            # Check for profile icon or other logged-in element
            self.driver.find_element(By.ID, 'profile-nav-item')
            return True
        except NoSuchElementException:
            return False
        except WebDriverException:
            return False

    def get_industries(self):
        from .models import Lead
        with self.app.app_context():
            industries = db.session.query(Lead.industry).distinct().all()
            return [i[0] for i in industries if i[0]]

    def get_company_size(self):
        # Try to extract company size from the company LinkedIn page
        try:
            size_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'employees') or contains(text(), 'employee')]")
            size_text = size_elem.text.lower()
            # Extract number range, e.g., '51-200 employees'
            match = re.search(r'(\d+[\-,]?\d*)\s*employees', size_text)
            if match:
                size_range = match.group(1)
                # Convert to average size for logic
                if '-' in size_range:
                    low, high = map(int, size_range.replace(',', '').split('-'))
                    avg_size = (low + high) // 2
                else:
                    avg_size = int(size_range.replace(',', ''))
                return avg_size
        except Exception:
            pass
        return None

    def is_preferred_decision_maker(self, title, company_size):
        # For large companies, prefer department heads; for small, prefer C-level/founder
        title_lower = title.lower()
        if company_size is not None:
            if company_size >= 200:
                # Large company: prefer 'head', 'vp', 'director', 'regional', 'department', 'manager'
                return any(k in title_lower for k in ['head', 'vp', 'director', 'regional', 'department', 'manager'])
            else:
                # Small company: prefer 'ceo', 'founder', 'owner', 'president', 'principal', 'partner', 'c-level', 'executive'
                return any(k in title_lower for k in ['ceo', 'founder', 'owner', 'president', 'principal', 'partner', 'chief', 'executive'])
        return True  # If size unknown, accept all decision-makers

    def scrape(self):
        self.start_driver(headless=False)
        self.driver.get('https://www.linkedin.com/')
        print('Waiting 2 minutes for manual LinkedIn login...')
        time.sleep(120)
        self.ensure_logged_in()
        industries = self.get_industries()
        for industry in industries:
            if self._stop_flag:
                break
            self.scrape_industry(industry)
        self.driver.quit()

    def is_robot_check(self):
        # Detect LinkedIn's anti-bot/CAPTCHA page by common elements/text
        try:
            if 'robot' in self.driver.page_source.lower() or 'captcha' in self.driver.page_source.lower():
                return True
            # Look for common LinkedIn robot/CAPTCHA selectors
            if self.driver.find_elements(By.CSS_SELECTOR, 'div.captcha-internal'):
                return True
            if self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Are you a robot') or contains(text(), 'unusual activity')]" ):
                return True
        except Exception:
            pass
        return False

    def is_duplicate_lead(self, db, ScrapedLead, company_name, key_person, role, linkedin_url):
        # Check for duplicate by company + person + role + LinkedIn URL
        query = db.session.query(ScrapedLead).filter(
            ScrapedLead.company_name == company_name,
            ScrapedLead.key_person == key_person,
            ScrapedLead.role == role,
            ScrapedLead.linkedin_url == linkedin_url
        )
        return db.session.query(query.exists()).scalar()

    def send_connection_request(self, profile_url, custom_message=None):
        self.driver.get(profile_url)
        time.sleep(random.uniform(3, 6))
        try:
            # Check if already connected
            if self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Message')]"):
                print(f'Already connected to {profile_url}')
                return 'already_connected'
            # Find and click Connect button
            connect_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Connect') or contains(text(), 'Connect')]")
            connect_btn.click()
            time.sleep(random.uniform(2, 4))
            # If a message is to be sent
            if custom_message:
                add_note_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Add a note') or contains(text(), 'Add a note')]")
                add_note_btn.click()
                time.sleep(1)
                note_box = self.driver.find_element(By.ID, 'custom-message')
                note_box.clear()
                note_box.send_keys(custom_message)
                send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send now') or contains(text(), 'Send')]")
                send_btn.click()
            else:
                send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send now') or contains(text(), 'Send')]")
                send_btn.click()
            print(f'Connection request sent to {profile_url}')
            time.sleep(random.uniform(2, 5))
            return 'sent'
        except Exception as e:
            print(f'Could not send connection request to {profile_url}: {e}')
            return 'failed'

    INDUSTRY_TITLES = {
        "Photography Studios": [
            "Studio Manager", "Post Production Manager", "Retouching Lead", "Art Director", "Creative Director", "Head of Studio", "Production Manager"
        ],
        "Software": [
            "CTO", "VP Engineering", "Head of Development", "Product Manager", "Chief Technology Officer", "Lead Developer", "Engineering Manager"
        ],
        "Marketing Firms": [
            "Head of Marketing", "CMO", "Brand Manager", "Account Director", "Marketing Director", "Digital Marketing Manager", "Strategy Director"
        ],
        "Creative Agencies": [
            "Creative Director", "Art Director", "Head of Creative", "Design Director", "Lead Designer", "Chief Creative Officer"
        ],
        "E-commerce / Online Retail": [
            "E-commerce Director", "Head of E-commerce", "Operations Manager", "Head of Online Sales", "Digital Director"
        ],
        "Real Estate": [
            "Managing Director", "Broker Owner", "Principal", "Head of Sales", "Regional Director", "Real Estate Manager"
        ],
        "Fashion & Apparel": [
            "Fashion Director", "Head of Design", "Brand Manager", "Creative Director", "Production Manager"
        ],
        "Jewelry & Luxury Goods": [
            "Brand Director", "Head of Retail", "Creative Director", "Store Manager", "Merchandising Manager"
        ],
        "IT Services": [
            "IT Director", "Head of IT", "Chief Information Officer", "IT Manager", "Solutions Architect"
        ],
        "Animation / 3D": [
            "Head of Animation", "Animation Director", "3D Lead", "VFX Supervisor", "Studio Manager"
        ],
    }
    GLOBAL_DECISION_MAKER_KEYWORDS = [
        'ceo', 'chief', 'cmo', 'coo', 'cto', 'vp', 'president', 'founder', 'owner', 'managing partner',
        'director', 'head', 'lead', 'senior', 'executive', 'principal', 'partner', 'strategy', 'buyer',
        'talent acquisition', 'recruiter', 'studio manager', 'art director', 'client services', 'project manager'
    ]

    NLP_DECISION_PHRASES = [
        'leads', 'manages', 'oversees', 'responsible for', 'decision maker', 'budget authority',
        'team lead', 'head of', 'in charge of', 'supervises', 'runs', 'directs', 'owner of', 'founder of'
    ]

    PROFILE_DECISION_PHRASES = [
        'decision maker', 'responsible for', 'leads', 'manages', 'oversees', 'budget authority',
        'team lead', 'department head', 'hiring manager', 'key contact', 'final approval', 'strategic direction',
        'business owner', 'founder', 'principal', 'executive decision', 'client acquisition', 'project lead'
    ]

    def is_decision_maker(self, title, industry=None):
        title_lower = title.lower()
        # Check global keywords
        if any(keyword in title_lower for keyword in self.GLOBAL_DECISION_MAKER_KEYWORDS):
            return True
        # Check industry-specific titles
        if industry and industry in self.INDUSTRY_TITLES:
            for keyword in self.INDUSTRY_TITLES[industry]:
                if keyword.lower() in title_lower:
                    return True
        # NLP scoring: look for decision-maker phrases
        nlp_score = sum(1 for phrase in self.NLP_DECISION_PHRASES if phrase in title_lower)
        if nlp_score >= 1:
            return True
        return False

    def profile_section_indicates_decision_maker(self, profile_url):
        self.driver.get(profile_url)
        time.sleep(random.uniform(3, 6))
        try:
            # Expand About section if available
            try:
                about_expand = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'See more about') or contains(text(), 'See more')]")
                about_expand.click()
                time.sleep(1)
            except Exception:
                pass
            about_text = ''
            try:
                about_elem = self.driver.find_element(By.CSS_SELECTOR, 'section.pv-about-section, div.display-flex.mt2 ul.pv-text-details__left-panel')
                about_text = about_elem.text.lower()
            except Exception:
                pass
            # Expand Experience section if available
            try:
                exp_expand = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'See more experience') or contains(text(), 'See more')]")
                exp_expand.click()
                time.sleep(1)
            except Exception:
                pass
            exp_text = ''
            try:
                exp_elem = self.driver.find_element(By.CSS_SELECTOR, 'section.pv-profile-section.experience-section, section#experience')
                exp_text = exp_elem.text.lower()
            except Exception:
                pass
            # Check for decision-maker phrases
            combined_text = about_text + ' ' + exp_text
            for phrase in self.PROFILE_DECISION_PHRASES:
                if phrase in combined_text:
                    return True
        except Exception as e:
            print(f'Error analyzing profile sections for {profile_url}: {e}')
        return False

    def random_mouse_move(self):
        # Move to a random element on the page
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'a, button, img, div')
        if elements:
            elem = random.choice(elements)
            ActionChains(self.driver).move_to_element(elem).perform()
            time.sleep(random.uniform(0.5, 2))

    def random_hover(self, selector):
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            elem = random.choice(elements)
            ActionChains(self.driver).move_to_element(elem).perform()
            time.sleep(random.uniform(1, 3))

    def slow_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

    def random_idle(self):
        if random.random() < 0.1:  # 10% chance to idle
            print('Simulating user reading/thinking...')
            time.sleep(random.uniform(10, 30))

    def random_scroll(self):
        # Scroll up and down randomly
        for _ in range(random.randint(1, 3)):
            direction = random.choice(['up', 'down'])
            if direction == 'down':
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            else:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_UP)
            time.sleep(random.uniform(0.5, 1.5))

    def random_tab_switch(self):
        # Simulate switching tabs and pausing
        if len(self.driver.window_handles) > 1 and random.random() < 0.2:
            main = self.driver.current_window_handle
            others = [h for h in self.driver.window_handles if h != main]
            if others:
                tab = random.choice(others)
                self.driver.switch_to.window(tab)
                print('Simulating user switching to another tab...')
                time.sleep(random.uniform(2, 8))
                self.driver.switch_to.window(main)

    def random_mistake_click(self):
        # Occasionally click a non-target element and go back
        if random.random() < 0.1:
            elements = self.driver.find_elements(By.CSS_SELECTOR, 'a, button')
            if elements:
                elem = random.choice(elements)
                try:
                    elem.click()
                    print('Simulating user mistake click...')
                    time.sleep(random.uniform(2, 5))
                    self.driver.back()
                    time.sleep(random.uniform(1, 3))
                except Exception:
                    pass

    # Integrate these into the scraping flow:
    # - Call random_mouse_move() and random_idle() after major actions (page load, click, etc.)
    # - Use slow_type() when entering messages/comments
    # - Occasionally skip actions (e.g., skip connecting with a person)

    COMMENT_TEMPLATES = [
        "Great insight, thanks for sharing!",
        "Congrats on your recent project—very inspiring.",
        "This is a valuable perspective for our industry.",
        "Impressive work, your team is doing amazing things!",
        "Thanks for posting this update, learned a lot.",
        "Love the innovation here—keep it up!",
        "Your leadership really shows in this post.",
        "Appreciate you sharing your experience!",
        "This resonates with what we're seeing in the market.",
        "Excited to see what's next for your company!"
    ]
    COMMENT_KEYWORDS = [
        'hiring', 'project', 'collaboration', 'launch', 'team', 'growth', 'expanding', 'opportunity', 'success', 'award', 'milestone', 'client', 'innovation', 'leadership', 'strategy', 'partnership'
    ]
    MESSAGE_TEMPLATES = [
        "Hi {name}, thanks for connecting! I really admire the work you're doing at {company}. If you ever want to discuss {industry} trends or share insights, I'd love to chat.",
        "Hello {name}, I enjoyed your recent post on {topic}. Looking forward to learning more about your journey at {company}!",
        "Hi {name}, if you ever need a partner for {industry} projects or want to brainstorm ideas, feel free to reach out!",
        "Hi {name}, your leadership in {industry} is impressive. If I can ever be a resource, please let me know!",
        "Hello {name}, congrats on your recent achievements at {company}. Wishing you continued success!"
    ]
    MAX_COMMENTS_PER_DAY = 10
    MAX_MESSAGES_PER_DAY = 10

    # Add industry-specific comment templates
    INDUSTRY_COMMENT_TEMPLATES = {
        "Photography Studios": [
            "Stunning visuals! Your studio's work is always inspiring.",
            "Great to see innovation in post-production!",
            "Love the creative direction in your recent shoot."
        ],
        "Software": [
            "Impressive product update—software innovation at its best!",
            "Great insights on automation trends.",
            "Your team's work in software is really moving the industry forward."
        ],
        "Marketing Firms": [
            "Excellent campaign results! Inspiring marketing leadership.",
            "Love the creative strategy behind your recent project.",
            "Great to see data-driven marketing in action."
        ],
        "E-commerce / Online Retail": [
            "Congrats on your recent sales milestone!",
            "Love the customer-centric approach in your latest post.",
            "Great insights on e-commerce growth."
        ],
        "Real Estate": [
            "Impressive property showcase!",
            "Great to see innovation in real estate marketing.",
            "Congrats on your recent closing!"
        ],
        "Fashion & Apparel": [
            "Stunning collection! Love the new designs.",
            "Great to see sustainable fashion initiatives.",
            "Your brand's creativity really stands out."
        ],
        # Add more as needed
    }

    def generate_contextual_comment(self, post_text, industry=None):
        doc = nlp(post_text)
        # Try to find a project, event, or achievement
        for ent in doc.ents:
            if ent.label_ in ['PRODUCT', 'EVENT', 'WORK_OF_ART', 'ORG', 'AWARD']:
                return f"Congrats on your recent {ent.label_.lower()} '{ent.text}'! Very inspiring for the {industry or 'industry'} community."
            if ent.label_ == 'GPE':
                return f"Great to see innovation coming from {ent.text}!"
            if ent.label_ == 'DATE':
                return f"Exciting milestone in {ent.text}! Congrats to your team."
        # If no entity, fallback to industry or generic
        if industry and industry in self.INDUSTRY_COMMENT_TEMPLATES:
            return random.choice(self.INDUSTRY_COMMENT_TEMPLATES[industry])
        return random.choice(self.COMMENT_TEMPLATES)

    def comment_on_posts(self, profile_url, industry=None):
        self.driver.get(profile_url)
        time.sleep(random.uniform(3, 6))
        self.random_mouse_move()
        self.random_idle()
        self.random_scroll()
        posts = self.driver.find_elements(By.CSS_SELECTOR, 'div.feed-shared-update-v2')
        comments_left = 0
        for post in posts:
            if comments_left >= self.MAX_COMMENTS_PER_DAY:
                break
            post_text = post.text.lower()
            if any(keyword in post_text for keyword in self.COMMENT_KEYWORDS):
                try:
                    comment_btn = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'Comment') or contains(text(), 'Comment')]")
                    comment_btn.click()
                    time.sleep(random.uniform(1, 2))
                    comment_box = self.driver.find_element(By.CSS_SELECTOR, 'div.comments-comment-box__editor')
                    # Use spaCy to generate a context-aware comment
                    comment = self.generate_contextual_comment(post_text, industry)
                    self.slow_type(comment_box, comment)
                    submit_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Post comment') or contains(text(), 'Post')]")
                    submit_btn.click()
                    print(f'Commented on post: {comment}')
                    comments_left += 1
                    self.random_idle()
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print(f'Could not comment on post: {e}')
                    continue

    def send_message(self, profile_url, name, company, industry, topic=None, message_override=None):
        self.driver.get(profile_url)
        time.sleep(random.uniform(3, 6))
        self.random_mouse_move()
        self.random_idle()
        self.random_scroll()
        try:
            message_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Message') or contains(text(), 'Message')]")
            message_btn.click()
            time.sleep(random.uniform(1, 2))
            message_box = self.driver.find_element(By.CSS_SELECTOR, 'div.msg-form__contenteditable')
            if message_override:
                msg = message_override
            else:
                template = random.choice(self.MESSAGE_TEMPLATES)
                msg = template.format(name=name, company=company, industry=industry, topic=topic or industry)
            self.slow_type(message_box, msg)
            send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send') or contains(text(), 'Send')]")
            send_btn.click()
            print(f'Sent message to {name}: {msg}')
            self.random_idle()
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f'Could not send message to {profile_url}: {e}')

    def scrape_industry(self, industry):
        from .models import ScrapedLead, db
        search_url = f'https://www.linkedin.com/search/results/companies/?keywords={industry}&origin=GLOBAL_SEARCH_HEADER&geoUrn=%5B%22103644278%22%5D'
        self.driver.get(search_url)
        self.random_mouse_move()
        self.random_idle()
        self.random_scroll()
        self.random_tab_switch()
        self.random_mistake_click()
        time.sleep(random.uniform(3, 6))
        leads_collected = 0
        max_leads = 50  # Daily quota, can be adjusted
        connections_sent = 0
        max_connections = 20  # Daily connection request limit
        page = 1
        comments_left = 0
        messages_left = 0
        while leads_collected < max_leads:
            if self.is_robot_check():
                print('LinkedIn anti-bot/CAPTCHA detected! Please solve it manually in the browser. Pausing...')
                while self.is_robot_check():
                    time.sleep(10)
                print('CAPTCHA solved, resuming scraping.')
            for _ in range(3):
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(random.uniform(2, 4))
            companies = self.driver.find_elements(By.CSS_SELECTOR, 'div.entity-result__content')
            for company in companies:
                if leads_collected >= max_leads:
                    break
                try:
                    name_elem = company.find_element(By.CSS_SELECTOR, 'span.entity-result__title-text a.app-aware-link')
                    company_name = name_elem.text.strip()
                    linkedin_url = name_elem.get_attribute('href')
                    website = ''
                    hiring = 'Unknown'
                    subtitle = company.find_elements(By.CSS_SELECTOR, 'div.entity-result__primary-subtitle')
                    if subtitle:
                        industry_text = subtitle[0].text.strip()
                    else:
                        industry_text = industry
                    self.driver.execute_script('window.open(arguments[0]);', linkedin_url)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.random_mouse_move()
                    self.random_idle()
                    self.random_scroll()
                    self.random_tab_switch()
                    self.random_mistake_click()
                    time.sleep(random.uniform(3, 6))
                    try:
                        about_tab = self.driver.find_element(By.XPATH, "//a[contains(@href, '/about/')]")
                        about_tab.click()
                        time.sleep(random.uniform(2, 4))
                        about_section = self.driver.find_element(By.CSS_SELECTOR, 'section.org-page-details__definition-section')
                        links = about_section.find_elements(By.CSS_SELECTOR, 'a')
                        for link in links:
                            href = link.get_attribute('href')
                            if href and ('http://' in href or 'https://' in href):
                                website = href
                                break
                    except Exception:
                        pass
                    try:
                        jobs_tab = self.driver.find_element(By.XPATH, "//a[contains(@href, '/jobs/')]")
                        jobs_tab.click()
                        time.sleep(random.uniform(2, 4))
                        jobs_section = self.driver.find_element(By.CSS_SELECTOR, 'section.jobs-tab__content')
                        if 'hiring' in jobs_section.text.lower() or 'open jobs' in jobs_section.text.lower():
                            hiring = 'Yes'
                    except Exception:
                        pass
                    try:
                        posts_tab = self.driver.find_element(By.XPATH, "//a[contains(@href, '/posts/')]")
                        posts_tab.click()
                        time.sleep(random.uniform(2, 4))
                        posts_section = self.driver.find_element(By.CSS_SELECTOR, 'div.feed-shared-update-v2')
                        if 'hiring' in posts_section.text.lower():
                            hiring = 'Yes'
                    except Exception:
                        pass
                    decision_makers_found = 0
                    try:
                        people_tab = self.driver.find_element(By.XPATH, "//a[contains(@href, '/people/')]")
                        people_tab.click()
                        time.sleep(random.uniform(3, 6))
                        people_cards = self.driver.find_elements(By.CSS_SELECTOR, 'li.org-people-profiles-module__profile-item')
                        # Shuffle the list to simulate random order
                        random.shuffle(people_cards)
                        for person in people_cards:
                            if decision_makers_found >= 3:
                                break
                            try:
                                name = person.find_element(By.CSS_SELECTOR, 'div.t-16.t-black.t-bold').text.strip()
                                title = person.find_element(By.CSS_SELECTOR, 'div.t-14.t-black--light.t-normal').text.strip()
                                profile_link = person.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                                company_size = self.get_company_size()
                                is_dm = self.is_decision_maker(title, industry_text)
                                is_profile_dm = self.profile_section_indicates_decision_maker(profile_link) if not is_dm else False
                                is_preferred = self.is_preferred_decision_maker(title, company_size)
                                if (is_dm or is_profile_dm) and is_preferred:
                                    with self.app.app_context():
                                        # Extract About section
                                        about_text = ''
                                        try:
                                            about_elem = self.driver.find_element(By.CSS_SELECTOR, 'section.pv-about-section, div.display-flex.mt2 ul.pv-text-details__left-panel')
                                            about_text = about_elem.text.strip()
                                        except Exception:
                                            pass
                                        # Extract most recent post
                                        recent_post_text = ''
                                        try:
                                            posts = self.driver.find_elements(By.CSS_SELECTOR, 'div.feed-shared-update-v2')
                                            if posts:
                                                recent_post_text = posts[0].text.strip()
                                        except Exception:
                                            pass
                                        if not self.is_duplicate_lead(db, ScrapedLead, company_name, name, title, profile_link):
                                            lead = ScrapedLead(
                                                company_name=company_name,
                                                website=website,
                                                industry=industry_text,
                                                hiring=hiring,
                                                key_person=name,
                                                role=title,
                                                linkedin_url=profile_link,
                                                about=about_text,
                                                recent_post=recent_post_text,
                                                status='new'
                                            )
                                            db.session.add(lead)
                                            db.session.commit()
                                            leads_collected += 1
                                            decision_makers_found += 1
                                            # Send connection request if under daily limit
                                            if random.random() < 0.85:  # 85% chance to send connection, 15% skip
                                                if connections_sent < max_connections:
                                                    msg = f"Hi {name}, I'd love to connect and discuss {industry_text} opportunities!"
                                                    connect_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Connect') or contains(text(), 'Connect')]")
                                                    connect_btn.click()
                                                    time.sleep(random.uniform(2, 4))
                                                    if custom_message:
                                                        add_note_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Add a note') or contains(text(), 'Add a note')]")
                                                        add_note_btn.click()
                                                        time.sleep(1)
                                                        note_box = self.driver.find_element(By.ID, 'custom-message')
                                                        note_box.clear()
                                                        self.slow_type(note_box, msg)
                                                        send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send now') or contains(text(), 'Send')]")
                                                        send_btn.click()
                                                    else:
                                                        send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send now') or contains(text(), 'Send')]")
                                                        send_btn.click()
                                                    print(f'Connection request sent to {profile_link}')
                                                    connections_sent += 1
                                                    time.sleep(random.uniform(5, 15))
                                                else:
                                                    print(f'Skipping connection request for {profile_link} to mimic human randomness.')
                                        else:
                                            print(f'Duplicate lead skipped: {company_name} - {name} - {title}')
                            except Exception:
                                continue
                            if random.random() < 0.5 and comments_left < self.MAX_COMMENTS_PER_DAY:
                                print(f'Attempting to comment on posts for {name}...')
                                self.comment_on_posts(profile_link, industry_text)
                                comments_left += 1
                            profile_data = {
                                'name': name, 'company': company_name, 'about': about_text, 'recent_post': recent_post_text,
                                'industry': industry_text, 'role': title
                            }
                            best_variant = predict_best_variant()
                            ai_message, message_variant = ai_generate_message(profile_data, forced_variant=best_variant)
                            if random.random() < 0.5 and messages_left < self.MAX_MESSAGES_PER_DAY:
                                print(f'Attempting to send AI-generated message to {name}...')
                                self.send_message(profile_link, name, company_name, industry_text, topic=None, message_override=ai_message)
                                messages_left += 1
                            # Save the message and variant to the lead
                            lead = ScrapedLead(
                                company_name=company_name, website=website, industry=industry_text,
                                hiring=hiring, key_person=name, role=title, linkedin_url=profile_link,
                                about=about_text, recent_post=recent_post_text, # New fields
                                ai_message=ai_message, message_variant=message_variant, # Store for A/B testing
                                status='new'
                            )
                            db.session.add(lead)
                            db.session.commit()
                            # Placeholder for reply logging (to be implemented in UI or via automation):
                            # lead.message_reply = <reply_text>
                            # db.session.commit()
                    except Exception as e:
                        print(f'No people tab or error extracting people: {e}')
                    if decision_makers_found == 0:
                        with self.app.app_context():
                            if not self.is_duplicate_lead(db, ScrapedLead, company_name, '', '', linkedin_url):
                                lead = ScrapedLead(
                                    company_name=company_name,
                                    website=website,
                                    industry=industry_text,
                                    hiring=hiring,
                                    key_person='',
                                    role='',
                                    linkedin_url=linkedin_url,
                                    status='new'
                                )
                                db.session.add(lead)
                                db.session.commit()
                                leads_collected += 1
                            else:
                                print(f'Duplicate company skipped: {company_name}')
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print(f'Error scraping company: {e}')
                    continue
            try:
                next_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Next') and not(@disabled)]")
                if not next_btn.is_enabled():
                    break
                next_btn.click()
                page += 1
                print(f'Paginating to page {page} for industry {industry}')
                if page % 3 == 0:
                    print('Taking a longer break to avoid detection...')
                    time.sleep(random.uniform(60, 120))
                else:
                    time.sleep(random.uniform(5, 15))
            except Exception:
                print('No more pages or Next button not found.')
                break 