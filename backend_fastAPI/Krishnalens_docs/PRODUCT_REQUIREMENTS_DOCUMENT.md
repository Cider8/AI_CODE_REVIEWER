# KrishnaLens: Product Requirements Document

| | |
|---|---|
| **Product** | KrishnaLens, an AI code reviewer |
| **Document type** | Product Requirements Document (PRD) |
| **Version** | 1.0 |
| **Status** | Draft for review |
| **Perspective** | Describes the product from the user's side only: what people see, do and get |

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [Purpose of this document](#11-purpose-of-this-document)
   - 1.2 [Scope](#12-scope)
   - 1.3 [Intended readers](#13-intended-readers)
   - 1.4 [How to read the requirements](#14-how-to-read-the-requirements)
2. [Terminology and Keywords](#2-terminology-and-keywords)
3. [Product Overview](#3-product-overview)
   - 3.1 [Vision](#31-vision)
   - 3.2 [The problem](#32-the-problem)
   - 3.3 [Product goals](#33-product-goals)
   - 3.4 [Non-goals](#34-non-goals)
4. [Users and Personas](#4-users-and-personas)
5. [Key User Journeys](#5-key-user-journeys)
6. [Functional Requirements](#6-functional-requirements)
   - 6.1 [Welcome page](#61-welcome-page)
   - 6.2 [Creating an account](#62-creating-an-account)
   - 6.3 [Signing in and out](#63-signing-in-and-out)
   - 6.4 [Navigation](#64-navigation)
   - 6.5 [Requesting a new review](#65-requesting-a-new-review)
   - 6.6 [The review report](#66-the-review-report)
   - 6.7 [Chatting about a review](#67-chatting-about-a-review)
   - 6.8 [Review history](#68-review-history)
   - 6.9 [Dashboard](#69-dashboard)
   - 6.10 [Collections](#610-collections)
   - 6.11 [Profile and settings](#611-profile-and-settings)
   - 6.12 [Deleting an account](#612-deleting-an-account)
7. [Messages, Feedback and Error States](#7-messages-feedback-and-error-states)
8. [Product Rules and Limits](#8-product-rules-and-limits)
9. [Quality Requirements](#9-quality-requirements)
10. [Out of Scope](#10-out-of-scope)
11. [Success Measures](#11-success-measures)
12. [Assumptions and Dependencies](#12-assumptions-and-dependencies)
13. [Open Questions and Known Issues](#13-open-questions-and-known-issues)
14. [Appendix](#14-appendix)
    - A. [Supported languages](#a-supported-languages)
    - B. [Score bands](#b-score-bands)
    - C. [Severity and impact levels](#c-severity-and-impact-levels)
    - D. [Requirement index](#d-requirement-index)

---

## 1. Introduction

### 1.1 Purpose of this document
This document describes what KrishnaLens does for the people who use it: what
they can do, what they will see, the rules the product follows, and how well
it must behave. It is the single reference for what "done" means for each
feature.

### 1.2 Scope
Covered: everything a visitor or signed-in member can see and do in KrishnaLens,
from the welcome page to deleting their account.

Not covered: how the product is built, hosted or operated.

### 1.3 Intended readers
Product owners, designers, testers, support staff, and anyone deciding what
KrishnaLens should do next.

### 1.4 How to read the requirements
- Each requirement has an ID such as **PR-REV-03**. IDs never change, so
  they can be quoted in discussions and test plans.
- **Must** means required for the product to be acceptable. **Should**
  means expected but negotiable. **May** means optional.
- *Acceptance* notes describe how a tester can confirm a requirement is met.

---

## 2. Terminology and Keywords

| Term | Meaning |
|---|---|
| **KrishnaLens** | The product described in this document. |
| **Visitor** | Someone using KrishnaLens without being signed in. A visitor can only see the welcome, sign-in and sign-up pages. |
| **Member** | A person who has created an account and is signed in. |
| **Account** | A member's identity in KrishnaLens: name, email address, password and preferences. |
| **Code snippet** | A piece of program code that a member pastes in for review. |
| **Language** | The programming language a snippet is written in, such as Python or Java. The member picks it. |
| **Review** | One AI analysis of one snippet, saved to the member's account. |
| **Review report** | The page that shows everything in a review. |
| **Score** | A number from 0 to 100 that sums up a snippet's quality. Higher is better. |
| **Bug** | A mistake in the code that may cause wrong behaviour or a crash. |
| **Security issue** | A weakness an attacker could exploit, such as a password written into the code. |
| **Performance issue** | Something that makes the code slower or more resource-hungry than it needs to be. |
| **Severity** | How serious a bug is: low, medium, high or critical. |
| **Impact** | How much a performance issue matters: low, medium or high. |
| **Improvement tip** | A general suggestion for better style or practice. |
| **Improved version** | A rewritten copy of the member's snippet with the suggested fixes applied. |
| **Complexity** | A short estimate of how the code's running time and memory use grow as its input grows (for example "O(n)"). |
| **Tags** | Short topic labels the AI attaches to a review, such as "recursion" or "sorting". |
| **Review chat** | A conversation in which the member asks the AI follow-up questions about one review. |
| **Daily chat allowance** | The number of chat questions a member may ask per day across all reviews. |
| **History** | The page listing all of a member's reviews. |
| **Dashboard** | The page summarising a member's progress over time. |
| **Common weakness** | A kind of bug or security problem (e.g. "Off-by-one error", "SQL Injection") that has come up in at least two of a member's reviews. |
| **Collection** | A named folder a member creates to group related reviews, such as "Interview Practice". |
| **Preferred languages** | Languages a member marks on their profile as the ones they mainly use. |
| **Danger zone** | The area of the profile page holding the irreversible action of deleting the account. |

---

## 3. Product Overview

### 3.1 Vision
Every developer gets a patient, expert reviewer for any snippet they write,
available instantly, and can watch their skills improve over time.

### 3.2 The problem
- Developers, students especially, often have nobody to review their code.
- Human reviews are slow, inconsistent, and can feel judgmental.
- Feedback is usually forgotten after it's read, so progress is hard to see.

### 3.3 Product goals

| # | Goal |
|---|---|
| G1 | Turn a pasted snippet into a clear, structured review within moments. |
| G2 | Explain problems in plain language and show how to fix them. |
| G3 | Keep every review so members can return to it, search it and organise it. |
| G4 | Show members their progress over time. |
| G5 | Let members ask follow-up questions instead of being left with feedback they don't understand. |
| G6 | Keep each member's code and reviews private to them. |

### 3.4 Non-goals
- Reviewing whole projects, multiple files or code repositories.
- Running or testing the member's code.
- Team review, sharing or commenting between members.
- Replacing a human expert for safety-critical decisions.

---

## 4. Users and Personas

| Persona | Description | Main needs |
|---|---|---|
| **Priya, the student** | Learning to program, practising problem-solving exercises. | Understand mistakes, see the score improve, group practice work by topic. |
| **Arjun, the working developer** | Writes code for a living and wants a quick second opinion before sharing work. | Fast, specific feedback; security and performance warnings; a ready-to-use improved version. |
| **Meera, the interview candidate** | Preparing for technical interviews. | Feedback on efficiency (complexity), a way to organise practice by theme, follow-up questions. |

---

## 5. Key User Journeys

### J1: First review (new visitor)
1. The visitor lands on the welcome page and chooses **Get Started**.
2. They create an account and are signed in straight away.
3. They open **New Review**, pick a language, paste a snippet and choose **Analyze with AI**.
4. A progress message appears while the AI works.
5. The review report opens, showing the score, problems found and an improved version.

### J2: Understanding feedback
1. A member opens a review report and doesn't understand one of the security issues.
2. They open the chat on that report and ask, "Why is this dangerous?"
3. The AI answers using that snippet and its review, and the member asks more questions.

### J3: Tracking progress
1. A member who has done several reviews opens the **Dashboard**.
2. They see their average score, how their scores have changed over time, the languages they use most, and their latest reviews.

### J4: Organising practice
1. A member creates a collection called "Dynamic Programming".
2. From each relevant review report, they add the review to that collection.
3. Later, the **Collections** page shows all the reviews in it in one place.

### J5: Finding an old review
1. A member opens **History**, types part of a review title and filters by language.
2. They page through the results and open the review they wanted.

### J6: Leaving the product
1. A member opens **Profile**, goes to the danger zone and chooses **Delete My Account**.
2. They confirm twice.
3. Their account and all of their content are removed, and they are signed out.

---

## 6. Functional Requirements

### 6.1 Welcome page

| ID | Requirement | Priority |
|---|---|---|
| PR-WEL-01 | Visitors must see a welcome page explaining that KrishnaLens reviews code with AI for performance, security and best practice. | Must |
| PR-WEL-02 | The welcome page must offer **Get Started / Sign Up** and **Login**. | Must |
| PR-WEL-03 | The welcome page should show a sample of what reviewing a snippet looks like. | Should |
| PR-WEL-04 | The welcome page should name the product's creator and show a copyright notice. | Should |

### 6.2 Creating an account

| ID | Requirement | Priority |
|---|---|---|
| PR-ACC-01 | A visitor must be able to sign up with their **name**, **email address** and **password**. | Must |
| PR-ACC-02 | Each email address can belong to only one account. Signing up with an email that's already registered must show "Email already in use". | Must |
| PR-ACC-03 | Passwords must be at least 8 characters and contain at least one uppercase letter, one lowercase letter and one special character (such as `!`, `@`, `#`, `$`). | Must |
| PR-ACC-04 | If the password doesn't meet the rules, the member must be told **which rule failed**, in plain words (e.g. "Password must contain at least one special character"). If several rules fail, all of them must be listed. This applies at sign-up and when changing the password. | Must |
| PR-ACC-05 | A successful sign-up must sign the member in straight away and take them into the product. No separate sign-in step is needed. | Must |
| PR-ACC-06 | The sign-up page must link to the sign-in page for people who already have an account. | Must |
| PR-ACC-07 | Every field where a password is chosen (sign-up and change password) must show the same hint before the member types: "At least 8 characters, with an uppercase letter, a lowercase letter and a special character". | Must |

*Acceptance:* signing up with "password1" is refused with a message about the missing uppercase letter and special character. Signing up with "Password#1" succeeds.

### 6.3 Signing in and out

| ID | Requirement | Priority |
|---|---|---|
| PR-SIGN-01 | A member must be able to sign in with email and password. | Must |
| PR-SIGN-02 | A wrong email and a wrong password must give the same message, "Invalid email or password", so the product never reveals which email addresses are registered. | Must |
| PR-SIGN-03 | A member must stay signed in on that browser for **7 days**, even after closing it. After that they must sign in again. | Must |
| PR-SIGN-04 | When a member's sign-in has expired or is no longer valid, the next action they take must return them to the sign-in page. | Must |
| PR-SIGN-05 | A member must be able to sign out at any time. | Must |
| PR-SIGN-06 | A visitor who tries to open a members-only page must be sent to the sign-in page. | Must |

### 6.4 Navigation

| ID | Requirement | Priority |
|---|---|---|
| PR-NAV-01 | Signed-in members must always see a side menu with **Dashboard**, **New Review**, **History**, **Collections** and **Profile**, plus a **Sign out** action. | Must |
| PR-NAV-02 | The menu must highlight the page the member is on. | Should |
| PR-NAV-03 | While a page loads its content, a loading message must be shown instead of a blank screen. | Must |

### 6.5 Requesting a new review

| ID | Requirement | Priority |
|---|---|---|
| PR-REV-01 | A member must be able to enter an optional **title**, choose a **language** from a list, and paste their **code**. | Must |
| PR-REV-02 | The language list must include the languages in [Appendix A](#a-supported-languages). | Must |
| PR-REV-03 | If no title is given, the review must be named after its language, e.g. "Python Review". | Must |
| PR-REV-04 | Submitting with no code must be refused with "Please paste some code first." | Must |
| PR-REV-05 | While the AI works, the page must show that analysis is in progress ("AI is reviewing your code…"), and the submit button must not accept a second press. | Must |
| PR-REV-06 | When the analysis finishes, the member must be taken straight to the new review report. | Must |
| PR-REV-07 | If the analysis fails, the member must see "Analysis failed. Try again.", their pasted code must still be there, and nothing must be saved to their history. | Must |
| PR-REV-08 | Every successful review must be saved to the member's account automatically and update their dashboard. | Must |

### 6.6 The review report

| ID | Requirement | Priority |
|---|---|---|
| PR-RPT-01 | The report must show the review title, language and date. | Must |
| PR-RPT-02 | The report must show the **score** (0–100) in a colour that matches its band ([Appendix B](#b-score-bands)). | Must |
| PR-RPT-03 | The report must show a short **summary** (2–3 sentences) of overall quality. | Must |
| PR-RPT-04 | The report must list **bugs**. Each one shows its severity, a description, a suggested fix and, where known, the line number. | Must |
| PR-RPT-05 | The report must list **security issues**. Each one shows the kind of issue (e.g. "Hardcoded Secret"), a description, a fix and, where known, the line number. | Must |
| PR-RPT-06 | The report must list **performance issues**. Each one shows its impact level, a description and a suggestion. | Must |
| PR-RPT-07 | Where a section has nothing to report, it must say so positively, e.g. "✓ No bugs found". | Must |
| PR-RPT-08 | The report must list **improvement tips**. | Must |
| PR-RPT-09 | The report must show the **improved version** of the code, ready to copy. | Must |
| PR-RPT-10 | The report must show **complexity** for time and space, plus the review's **tags**. | Must |
| PR-RPT-11 | A member must be able to **delete** the review from the report after confirming "Delete this review?". Deleting a review also removes it from every collection, deletes its chat conversation and updates the dashboard (see PR-DSH-08). | Must |
| PR-RPT-12 | A member must be able to add the review to one of their **collections** from the report (see 6.10). | Must |
| PR-RPT-13 | A member must only ever see their own reviews. Opening someone else's review, or one that doesn't exist, must show "Review not found." | Must |

### 6.7 Chatting about a review

| ID | Requirement | Priority |
|---|---|---|
| PR-CHAT-01 | Every review report must include a chat area titled "Chat about this review". | Must |
| PR-CHAT-02 | The AI must answer questions using that review's snippet and summary. Questions unrelated to the review must get a short reply saying they're out of scope. | Must |
| PR-CHAT-03 | Each review has one ongoing conversation. Leaving and returning, or refreshing the page, must show the earlier messages in order. | Must |
| PR-CHAT-04 | The AI must take the recent conversation into account, so follow-up questions such as "and how do I fix that?" make sense. | Must |
| PR-CHAT-05 | A question must be 1–4,000 characters. | Must |
| PR-CHAT-06 | Each member may ask **20 questions per day** in total, across all reviews. The day resets at midnight UTC. | Must |
| PR-CHAT-07 | The chat must show how many questions remain today, and should draw attention to it when 3 or fewer remain. | Must / Should |
| PR-CHAT-08 | When the allowance runs out, the chat must say "Daily limit reached — back tomorrow" and explain that it resets at midnight UTC. | Must |
| PR-CHAT-09 | If the AI doesn't answer, the member must see "The AI service didn't respond. Please try again in a moment.", the unanswered question must not be added to the conversation, and it **must not count** against the daily chat allowance. | Must |
| PR-CHAT-10 | Pressing **Enter** should send the question. | Should |
| PR-CHAT-11 | An empty conversation must invite the member to start ("No messages yet — ask the first question."). | Should |

### 6.8 Review history

| ID | Requirement | Priority |
|---|---|---|
| PR-HIS-01 | History must list all of the member's reviews, newest first. Each entry shows its title, language, date and colour-coded score. | Must |
| PR-HIS-02 | History must show **10 reviews per page**, with **Prev** and **Next** buttons. | Must |
| PR-HIS-03 | A member must be able to **search** by review title. Search must ignore upper and lower case and match part of a title. | Must |
| PR-HIS-04 | A member must be able to **filter by language** using the full list in [Appendix A](#a-supported-languages), or choose "All". | Must |
| PR-HIS-05 | Selecting an entry must open its review report. | Must |
| PR-HIS-06 | A member must be able to delete a review from the list after confirming. The same clean-up as PR-RPT-11 applies. | Must |
| PR-HIS-07 | When there are no reviews, History must say "No reviews found" and link to "Submit your first code →". | Must |

### 6.9 Dashboard

| ID | Requirement | Priority |
|---|---|---|
| PR-DSH-01 | The dashboard must show four headline figures: **Total Reviews**, **Average Score** (out of 100), **Bugs Found** and **Security Issues** (totals across all reviews). | Must |
| PR-DSH-02 | The dashboard must show a **score over time** chart with one point per review, in order. | Must |
| PR-DSH-03 | The dashboard must show a **languages** breakdown: how many reviews the member has done in each language. | Must |
| PR-DSH-04 | The dashboard must list the **5 most recent reviews**, each linking to its report. | Must |
| PR-DSH-05 | A brand-new member must see friendly empty states ("No reviews yet", "No data yet") instead of zeros that look broken. | Must |
| PR-DSH-06 | If the dashboard can't load, the member must see "Failed to load stats." | Must |
| PR-DSH-07 | The dashboard must show the member's **common weaknesses**: up to 5 kinds of bug or security problem that have come up in **at least 2 different reviews**, most frequent first. Differences in capital letters or spacing don't make a new kind. Until something repeats, this area shows an empty state. | Must |
| PR-DSH-08 | All dashboard figures (headline totals, score over time, languages and common weaknesses) must describe only the reviews the member **still has**. Deleting a review must update them straight away. | Must |

### 6.10 Collections

| ID | Requirement | Priority |
|---|---|---|
| PR-COL-01 | A member must be able to create a collection with a **name** and an optional **description**. | Must |
| PR-COL-02 | The Collections page must list all of the member's collections, each showing the reviews inside it. Each review links to its report. | Must |
| PR-COL-03 | From a review report, a member must be able to choose one of their collections and add the review to it. Collections that already contain the review must be marked "(added)" and can't be picked again. | Must |
| PR-COL-04 | Adding a review must confirm success ("Added to *collection name*"). | Must |
| PR-COL-05 | Adding the same review to the same collection twice must never create a duplicate. | Must |
| PR-COL-06 | A member who has no collections must be prompted to create one when they try to organise a review. | Should |
| PR-COL-07 | A member must be able to delete a collection after confirming. Deleting a collection must **not** delete the reviews in it. | Must |
| PR-COL-08 | Empty states: "No collections yet. Create one to organise your reviews." and "No reviews in this collection yet." | Must |
| PR-COL-09 | A member must be able to **remove** a review from a collection, and **rename** a collection or change its description. A collection name can't be empty. An empty description clears it. | Must |
| PR-COL-10 | A review may belong to several collections at once. | Must |
| PR-COL-11 | Removing a review from a collection must never delete the review itself. | Must |

### 6.11 Profile and settings

| ID | Requirement | Priority |
|---|---|---|
| PR-PRF-01 | The profile page must show and let the member change their **display name**. | Must |
| PR-PRF-02 | A member must be able to choose **preferred languages** from the supported list, by toggling each on or off. | Must |
| PR-PRF-03 | Saving the profile must confirm "Profile saved!" or report "Save failed". | Must |
| PR-PRF-04 | A member must be able to **change their password** by entering the current password, a new password, and the new password again. | Must |
| PR-PRF-05 | If the two new-password entries differ, the member must see "Passwords don't match" before anything is sent. | Must |
| PR-PRF-06 | A wrong current password must be refused with "Current password is incorrect". | Must |
| PR-PRF-07 | The new password must follow the same rules as at sign-up (PR-ACC-03). | Must |
| PR-PRF-08 | A successful change must confirm "Password changed!". | Must |
| PR-PRF-09 | The email address can't be changed. | Must |
| PR-PRF-10 | The new-password field must show the password hint from PR-ACC-07. | Must |

### 6.12 Deleting an account

| ID | Requirement | Priority |
|---|---|---|
| PR-DEL-01 | The profile page must have a clearly marked **Danger Zone** with a **Delete My Account** action. | Must |
| PR-DEL-02 | Deletion must need **two confirmations**: first "This will permanently delete your account and ALL your reviews. Are you sure?", then "Last chance — this cannot be undone!". | Must |
| PR-DEL-03 | Deleting must permanently remove the account, all reviews, collections, dashboard progress and **all chat conversations**. | Must |
| PR-DEL-04 | After deletion the member must be signed out and must not be able to sign in again with the old details. | Must |
| PR-DEL-05 | If deletion fails, the member must see "Delete failed. Try again." and their account must stay as it was. | Must |

---

## 7. Messages, Feedback and Error States

| Situation | What the member sees |
|---|---|
| Wrong email or password | "Invalid email or password" |
| Email already registered | "Email already in use" |
| Password breaks a rule | A message naming the rule, e.g. "Password must contain at least one special character" |
| No code pasted | "Please paste some code first." |
| AI review fails | "Analysis failed. Try again." (pasted code is kept) |
| Review missing or not theirs | "Review not found." |
| Chat can't open | "Couldn't open the chat. Please try again." |
| Chat question not sent | "Couldn't send your message. Please try again." |
| AI chat not responding | "The AI service didn't respond. Please try again in a moment." |
| Daily chat allowance used | "Daily limit reached — back tomorrow" plus when it resets |
| Collection add fails | "Couldn't add to collection." |
| Dashboard can't load | "Failed to load stats." |
| Service temporarily unavailable | A clear "please try again later" message, never a blank page |
| Sign-in expired | Returned to the sign-in page |

General rules:
- Every action that changes something (save, add, delete) must confirm success or explain the failure.
- Every irreversible action (deleting a review, a collection or an account) must ask for confirmation first.
- Messages must use plain language and never show internal or technical detail.

---

## 8. Product Rules and Limits

| Rule | Value |
|---|---|
| Score range | 0–100 |
| Minimum password length | 8 characters |
| Password must contain | 1 uppercase letter, 1 lowercase letter, 1 special character |
| Stay signed in for | 7 days |
| Accounts per email address | 1 |
| Reviews shown per History page | 10 |
| Recent reviews on Dashboard | 5 |
| Chat questions per member per day | 20 (resets at midnight UTC; unanswered questions don't count) |
| Chat question length | 1–4,000 characters |
| Recent conversation the AI remembers | The last 6 messages |
| Conversations per review | 1 (kept and resumed; deleted along with the review) |
| Common weaknesses shown | Up to 5; a weakness must appear in at least 2 reviews |
| Dashboard figures cover | Reviews the member still has |
| Collections per review | No limit |
| Who can see a member's content | Only that member |

---

## 9. Quality Requirements

| ID | Area | Requirement |
|---|---|---|
| PR-Q-01 | **Privacy** | A member's code, reviews, collections and conversations must be visible only to that member. |
| PR-Q-02 | **Privacy** | The product must never reveal whether another person's review, collection or account exists. |
| PR-Q-03 | **Security** | Passwords must never be shown, emailed or stored in a readable form. |
| PR-Q-04 | **Speed** | Pages other than review creation should load within 2 seconds under normal conditions. |
| PR-Q-05 | **Speed** | A typical review (under 200 lines) should finish within 30 seconds, with progress shown the whole time. |
| PR-Q-06 | **Reliability** | A failed AI analysis or chat must never leave half-saved content behind. |
| PR-Q-07 | **Availability** | If the service is temporarily unable to store or fetch data, members must see a clear message rather than broken pages. |
| PR-Q-08 | **Consistency** | Dashboard figures must update as soon as a review is saved or deleted (PR-DSH-08). |
| PR-Q-09 | **Usability** | A new member must be able to finish their first review within 2 minutes of signing up, without help. |
| PR-Q-10 | **Accessibility** | Colour must never be the only signal. Scores show their number, severities show their label, and text has sufficient contrast. |
| PR-Q-11 | **Devices** | The product must work on current desktop versions of Chrome, Firefox, Safari and Edge. It should be usable on tablets. |
| PR-Q-12 | **Branding** | The product must be called **KrishnaLens** on every page, including the menu and the AI's name in the chat. |
| PR-Q-13 | **AI honesty** | The product should make clear that reviews are AI-generated and may contain mistakes. |

---

## 10. Out of Scope

- Signing in through other services (e.g. "Sign in with Google").
- Password reset by email ("Forgot password").
- Changing the email address on an account.
- Uploading files or connecting code repositories.
- Running the member's code.
- Sharing reviews or collections with other people, or working as a team.
- Exporting reviews (e.g. to a document file).
- Paid plans and billing.
- Mobile apps.
- Languages other than those in Appendix A.

---

## 11. Success Measures

| Measure | Target (first 3 months) |
|---|---|
| New members who complete a first review | ≥ 70% |
| Members who return within 7 days | ≥ 40% |
| Reviews that finish without an error | ≥ 97% |
| Reviews where the member opens the chat | ≥ 25% |
| Members who create at least one collection | ≥ 20% |
| Average score change for members with 10+ reviews | Upward trend |

---

## 12. Assumptions and Dependencies

- Members have a stable internet connection and a modern browser.
- Review and chat quality depend on an external AI service. If it is slow or down, reviews and chat are delayed or unavailable, while other features keep working.
- The AI's findings are advice, not guarantees. Members are responsible for checking suggestions before using them.
- Members paste code they are allowed to share with an AI service.

---

## 13. Open Questions and Known Issues

Points where the product didn't fully match this document, or where a decision was needed. All are decided and done, as of 4 Oct 2026.

| # | Topic | Detail | Status |
|---|---|---|---|
| Q1 | **Product name** | ✅ **Resolved 3 Oct 2026:** the product is named **KrishnaLens** everywhere (PR-Q-12). The menu and chat used to say a different name. | Done 4 Oct 2026: every page, the menu, the chat and the browser tab say KrishnaLens. |
| Q2 | **Password hint** | ✅ **Resolved 3 Oct 2026:** the sign-up and change-password fields show the same hint, which follows the 8-character rule (PR-ACC-07, PR-PRF-10). The change-password field used to say "Min 6 characters". | Done 4 Oct 2026: the hint is shown under both password fields. |
| Q3 | **Password error wording** | ✅ **Resolved 3 Oct 2026:** the member is told every password rule that failed, at sign-up and on password change (PR-ACC-04). | Done 4 Oct 2026: every failed rule is listed under the field, at sign-up and on password change. |
| Q4 | **Deleted reviews in collections** | ✅ **Resolved 3 Oct 2026:** deleting a review removes it from every collection and deletes its conversation (PR-RPT-11). | Done. |
| Q5 | **Dashboard after deletion** | ✅ **Resolved 3 Oct 2026:** the dashboard describes only the reviews the member still has, and deleting a review updates it straight away (PR-DSH-08). | Done. |
| Q6 | **Account deletion completeness** | ✅ **Resolved 3 Oct 2026:** deleting an account also removes every chat conversation (PR-DEL-03). | Done. |
| Q7 | **Common weaknesses** | ✅ **Resolved 3 Oct 2026:** defined as up to 5 kinds of bug or security problem that recur in at least 2 reviews (PR-DSH-07). Reviews created from now on carry the bug kinds this needs; older reviews contribute their security problems only. | Done 4 Oct 2026: shown on the dashboard as a ranked list, with an empty state. |
| Q8 | **Managing collections** | ✅ **Resolved 3 Oct 2026:** members can remove a review from a collection and rename or re-describe a collection (PR-COL-09, PR-COL-11). | Done 4 Oct 2026: the Collections page can rename, edit descriptions and remove reviews. |
| Q9 | **Chat allowance on failure** | ✅ **Resolved 3 Oct 2026:** a question the AI fails to answer is not counted (PR-CHAT-09). | Done. |
| Q10 | **History language filter** | ✅ **Resolved 3 Oct 2026:** the History filter offers the full language list (PR-HIS-04). | Done 4 Oct 2026: all 13 languages plus "All". |

---

## 14. Appendix

### A. Supported languages
JavaScript · TypeScript · Python · Java · C++ · C · Go · Rust · Ruby · PHP · Swift · Kotlin · C#

### B. Score bands

| Score | Band | Colour | Meaning |
|---|---|---|---|
| 70–100 | Good | Green | Solid code with few or minor issues |
| 40–69 | Fair | Amber | Works, but has noticeable problems worth fixing |
| 0–39 | Poor | Red | Serious problems; revise before use |

### C. Severity and impact levels

**Bug severity**

| Level | Meaning |
|---|---|
| Critical | Will crash or give wrong results in common use, or causes data loss |
| High | Wrong behaviour in realistic situations |
| Medium | Wrong behaviour in edge cases |
| Low | Minor problem or a risky pattern |

**Performance impact**

| Level | Meaning |
|---|---|
| High | Noticeably slow or wasteful, even on modest input |
| Medium | Slows down as input grows |
| Low | Small gain available |

### D. Requirement index

| Area | IDs |
|---|---|
| Welcome page | PR-WEL-01 – 04 |
| Account creation | PR-ACC-01 – 07 |
| Sign in / out | PR-SIGN-01 – 06 |
| Navigation | PR-NAV-01 – 03 |
| New review | PR-REV-01 – 08 |
| Review report | PR-RPT-01 – 13 |
| Review chat | PR-CHAT-01 – 11 |
| History | PR-HIS-01 – 07 |
| Dashboard | PR-DSH-01 – 08 |
| Collections | PR-COL-01 – 11 |
| Profile | PR-PRF-01 – 10 |
| Account deletion | PR-DEL-01 – 05 |
| Quality | PR-Q-01 – 13 |

---
## Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2 Oct 2026 | First version. |
| 1.1 | 3 Oct 2026 | Product name set to KrishnaLens (Q1). Password hint requirements added (PR-ACC-07, PR-PRF-10, Q2). |
| 1.2 | 3 Oct 2026 | All remaining open questions resolved (Q3–Q10): password error detail, clean-up on review deletion, dashboard reflects current reviews (PR-DSH-08), full account deletion, common weaknesses defined, collection remove/rename (PR-COL-11), failed chat questions not counted, full History language list. |
| 1.3 | 4 Oct 2026 | All open questions confirmed done on screen (Q1–Q3, Q7, Q8, Q10). |

*End of document.*
