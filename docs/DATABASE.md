# TravelSync Database Design

> "Store relationships, not just data."

---

# Overview

TravelSync is built around one core concept:

A Trip.

Everything else is connected to a trip.

Trip
│
├── Travelers
├── Preferences
├── Votes
├── Expenses
├── Chat
├── Memories
├── Challenges
├── Proposals
├── Notifications
└── Settings

---

# Users

Stores account information.

Fields

- user_id
- username
- email
- password_hash
- profile_picture
- bio
- created_at

Future

- badges
- achievements
- travel history

---

# Trips

Stores trip information.

Fields

- trip_id
- title
- owner_id
- source
- destination
- start_date
- end_date
- status

Status

Planning

Upcoming

Active

Completed

Archived

---

# Trip Members

Stores travelers inside a trip.

Fields

- member_id
- trip_id
- user_id
- role

Roles

Owner

Co-Organizer

Traveler

Guest

Future

Pending

Rejected

Removed

---

# Traveler Preferences

Individual traveler settings.

Fields

- preference_id
- user_id
- trip_id

Food

Budget

Interests

Energy Level

Accessibility

Challenge Enabled

Communication Preference

Privacy Preference

Trip Goal

---

# Proposals

Stores every proposal.

Fields

- proposal_id
- trip_id
- creator

Type

Restaurant

Hotel

Activity

Budget

Transportation

Entire Itinerary

Status

Open

Voting

Accepted

Rejected

Applied

Archived

---

# Votes

Stores votes.

Fields

- vote_id
- proposal_id
- user_id

Vote

Support

Oppose

Neutral

Abstain

Anonymous

Comment

Timestamp

---

# Expenses

Stores expenses.

Fields

- expense_id
- trip_id
- payer
- amount
- category
- participants

Future

Receipt

Currency

Location

---

# Expense Settlement

Stores calculated settlements.

Fields

- settlement_id
- from_user
- to_user
- amount
- status

---

# Chat

Stores messages.

Fields

- message_id
- trip_id
- sender

Content

Timestamp

Reply

Edited

Deleted

Anonymous

Future

Attachments

Voice

GIF

---

# Memories

Stores memories.

Fields

- memory_id
- trip_id

Type

Photo

Video

Story

Voice

AI Journal

Favorite

Timestamp

Location

---

# Photos

Stores uploaded media.

Fields

- photo_id
- memory_id
- uploader
- url

Future

AI tags

Faces

Places

---

# Challenges

Stores challenge definitions.

Fields

- challenge_id

Name

Description

Difficulty

Reward

Category

Team

Individual

Hidden

---

# Challenge Progress

Stores progress.

Fields

- progress_id
- challenge_id
- traveler
- xp
- completed

---

# Achievements

Stores earned achievements.

Fields

- achievement_id
- user_id
- title
- date

---

# Notifications

Stores notifications.

Fields

- notification_id
- user_id

Title

Content

Read

Created

---

# AI Stories

Stores generated stories.

Fields

- story_id
- trip_id

Day

Content

Created

---

# Time Capsules

Stores expectations.

Fields

- capsule_id
- trip_id
- user_id

Beginning Thoughts

Ending Thoughts

Reveal Date

---

# Connection Mode

Stores optional relationship features.

Fields

- connection_id

Enabled

Friendship Mode

Romance Mode

Trusted Friends

Private Notes

---

# Group Settings

Stores group configuration.

Fields

- setting_id
- trip_id

Governance Mode

Communication Mode

Voting Style

Challenge Enabled

Trip Pace

Privacy

Guest Policy

Owner Approval

---

# Reports

Stores community reports.

Fields

- report_id
- trip_id

Reporter

Target

Reason

Status

Owner Decision

---

# Future Tables

Travel History

Recommendations

Analytics

Travel Badges

Travel Statistics

AI Preferences

Wearable Data

Calendar Events

Offline Sync

Marketplace

---

# Database Principles

Every table should:

- Have a primary key
- Use foreign keys
- Track timestamps
- Avoid duplicate data
- Be easy to scale

The database should prioritize maintainability over premature optimization.