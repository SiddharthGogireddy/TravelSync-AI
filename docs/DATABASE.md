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

# Memories & Trip Journal (Step 79)

Stores persistent journal reflections and photo memories for trips.

### Database Table: `journal_entries` (SQLite `backend/data/memories.db`)

Engineered with WAL mode (`PRAGMA journal_mode=WAL;`), 30-second busy timeout, and process-level reentrant locking.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | Unique UUID identifier for the memory entry |
| `trip_id` | TEXT | NOT NULL, INDEXED | Associated trip ID |
| `author_id` | TEXT | NOT NULL, INDEXED | Authenticated user ID of the creator |
| `author_name` | TEXT | NULLABLE | Display name of the author at creation time |
| `day_number` | INTEGER | NULLABLE | Optional itinerary day number (e.g., Day 1, Day 2) |
| `attraction_name` | TEXT | NULLABLE | Optional referenced attraction name |
| `title` | TEXT | NULLABLE | Headline / title (max 200 characters) |
| `content` | TEXT | NOT NULL | Memory text / reflections (1 - 10,000 characters) |
| `photo_url` | TEXT | NULLABLE | Relative URL to the securely served photo attachment |
| `photo_filename` | TEXT | NULLABLE | Safe, sanitized unique filename on disk |
| `is_private` | INTEGER | NOT NULL DEFAULT 0 | `1` = private to author, `0` = shared with trip group |
| `created_at` | TEXT | NOT NULL (ISO UTC) | Timestamp of creation |
| `updated_at` | TEXT | NULLABLE (ISO UTC) | Timestamp of last edit |
| `is_deleted` | INTEGER | NOT NULL DEFAULT 0 | Soft-deletion flag |

### Indexes
- `idx_journal_trip_created` on `journal_entries(trip_id, created_at DESC)`
- `idx_journal_author` on `journal_entries(author_id)`
- `idx_journal_privacy` on `journal_entries(trip_id, is_private, is_deleted)`

---

# Photo Attachment Storage & Security

### Physical Storage Architecture
- Photo attachments are stored on the local filesystem under `backend/data/memories_uploads/` (customizable via `TRAVELSYNC_MEMORY_UPLOADS`).
- **Binary Isolation:** Photo binaries are NEVER stored inside trip JSON records or SQLite database cells.
- Filenames are randomly generated using cryptographic UUID4 (`<uuid4>.jpg`, `<uuid4>.png`, etc.).
- **Path Traversal Prevention:** Target file paths are strictly resolved and validated to ensure they remain inside the dedicated upload directory bounds. Traversal attempts (such as `..` or slash manipulation) are detected and rejected.

### Validation Rules & Storage Limits
- **File Size Limit:** Maximum 5 MB (5,242,880 bytes) per upload. Requests exceeding this limit receive HTTP 413.
- **Allowed Formats:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`.
- **Magic Byte Verification:** File header inspection confirms actual binary format:
  - JPEG: `\xff\xd8\xff`
  - PNG: `\x89PNG\r\n\x1a\n`
  - WebP: `RIFF....WEBP`
  - GIF: `GIF87a` / `GIF89a`
- Spoofed extensions (e.g. `.exe` disguised as `.png`) are rejected with HTTP 400.

### Privacy & Access Control
- **Private Entries (`is_private = 1`):** Visible exclusively to the author. Hidden from other trip members and excluded from activity feed and notifications.
- **Shared Entries (`is_private = 0`):** Visible to all authenticated members of the trip. Triggers an activity event in `activity_events` without leaking the private memory text into the notification summary.
- **Ownership:** Only the author can edit an entry. The author or the trip owner can delete entries.

### Backup & Retention Behavior
- **Database Backup:** Periodic snapshotting using SQLite online backup API or `VACUUM INTO 'backup.db'` with `PRAGMA wal_checkpoint(TRUNCATE)`.
- **Media Backup:** Synchronize `backend/data/memories_uploads/` to durable backup volumes or object storage buckets (e.g., via `rclone` or daily filesystem snapshots).
- **Soft Deletion:** Entries set `is_deleted = 1` so historical activity records and audit logs maintain relational consistency.

### Production Requirements & Cloud Migration
1. **Object Storage:** In production environments, replace local filesystem uploads with AWS S3, Google Cloud Storage, or Azure Blob Storage using presigned upload URLs.
2. **Database:** Migrate SQLite `journal_entries` table to PostgreSQL with Row-Level Security (RLS) or indexed JSONB for enterprise-grade clustering.
3. **CDN Integration:** Serve photo attachments via CloudFront or Cloudflare with token-based authorization and WebP/AVIF auto-transcoding.

---

# Memory Album & PDF Journal Export (Step 80)

Provides a dedicated chronological photo album view and downloadable PDF export of the trip journal.

### Memory Album Architecture
- **Query Endpoint:** `GET /trip/{trip_id}/memories/album` and `GET /trip/{trip_id}/journal/album`
- **Filtering:** Filters exclusively for non-deleted entries with valid photo attachments (`photo_filename IS NOT NULL AND photo_filename != ''`).
- **Privacy Enforcement:** Private photo memories (`is_private = 1`) are visible strictly to their creator. Shared photos (`is_private = 0`) are visible to all authenticated trip members.
- **Pagination & Day Filtering:** Supports `day_number`, `limit` (max 200), and `offset` for responsive grid browsing.

### PDF Journal Export Engine
- **Export Endpoint:** `GET /trip/{trip_id}/journal/pdf` and `GET /trip/{trip_id}/pdf/journal`
- **Storage Location:** Generated PDF documents are assembled under `backend/pdfs/` with collision-resistant UUID prefixes (`journal_<trip_id>_<uuid>.pdf`).
- **PDF Size Limits & Image Resizing:**
  - Standard page size: ReportLab standard A4 / Letter format.
  - Images are constrained to printable width bounds (max width 420 pt, max height 220 pt) with aspect-ratio preservation.
  - Memory-efficient streaming ensures documents with dozens of photos remain compact (typically 2 - 15 MB) without memory exhaustion.
- **Path Traversal Sandboxing:**
  - Every photo reference is verified through `get_memory_photo_path()`. References attempting directory traversal (`..`, absolute paths, slashes) are rejected with `None`.
  - Missing, corrupted, or unreachable photos are skipped with a graceful placeholder (`[Photo attachment unavailable]`), ensuring the PDF export never fails or exposes arbitrary system files.
- **Privacy at Export Time:**
  - SQL query strictly applies `(is_private = 0 OR author_id = :requester_id)`. Private entries of other trip members are physically excluded prior to PDF compilation.
- **Unicode & Typography:**
  - Uses `AppUnicode` / `JournalUnicode` TrueType fonts (Arial on Windows, DejaVuSans on Linux) with graceful fallback to standard typefaces.
  - HTML entities (`&`, `<`, `>`) and line breaks are sanitized to prevent XML parsing exceptions.
- **Storage & Cleanup:**
  - Export is strictly read-only: no database mutations or photo modifications occur.
  - Temporary PDFs can be purged via periodic cron job or background task after delivery.

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

# Activity Events and Notifications (Step 78)

Stores audit activity events and per-user in-app notifications.

## Activity Events (`activity_events`)

Table in `backend/data/activity.db` (SQLite with WAL mode and `PRAGMA busy_timeout=30000;`):

- `id`: TEXT PRIMARY KEY (UUID)
- `trip_id`: TEXT NOT NULL (Scoped to trip)
- `actor_id`: TEXT NOT NULL (Verified auth user ID)
- `actor_name`: TEXT (Display name or traveler name)
- `event_type`: TEXT NOT NULL (`member_joined`, `vote_submitted`, `chat_message_posted`, `attraction_comment_posted`, `conflicts_resolved`, `expense_added`, `itinerary_updated`)
- `title`: TEXT NOT NULL (Concise summary header)
- `summary`: TEXT NOT NULL (Redacted/safe event summary without leaking sensitive text)
- `target_type`: TEXT (`trip`, `attraction`, `voting`, `member`, `expense`, `itinerary`)
- `target_id`: TEXT (e.g. attraction name or item ID)
- `link`: TEXT (Deep anchor link, e.g. `/trip/{trip_id}#section-chat`)
- `metadata_json`: TEXT (Contextual payload)
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)

Indices:
- `idx_activity_trip_created`: `(trip_id, created_at)`
- `idx_activity_dedup`: `(trip_id, actor_id, event_type, target_id, created_at)`

## In-App User Notifications (`user_notifications`)

- `id`: TEXT PRIMARY KEY (UUID)
- `user_id`: TEXT NOT NULL (Recipient user ID)
- `trip_id`: TEXT NOT NULL (Trip reference)
- `event_id`: TEXT (Foreign reference to `activity_events.id`)
- `title`: TEXT NOT NULL
- `message`: TEXT NOT NULL (Safe summary)
- `link`: TEXT (Navigation anchor)
- `is_read`: INTEGER NOT NULL DEFAULT 0
- `read_at`: TEXT (ISO 8601 UTC when read)
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)

Indices:
- `idx_user_notif_unread`: `(user_id, is_read, created_at)`
- `idx_user_notif_trip`: `(user_id, trip_id, created_at)`

## Backup and Migration Requirements

1. **Storage Engine**:
   - `backend/data/activity.db` and `backend/data/chat.db` operate in WAL mode.
   - For point-in-time backups, use SQLite online backup API or copy `.db` alongside `.db-wal` while holding an exclusive lock, or use the `.backup` CLI command.
2. **Migration Path to PostgreSQL/RDBMS**:
   - Both tables use standard SQL data types (`TEXT`, `INTEGER`).
   - SQLite `metadata_json` translates directly to PostgreSQL `JSONB`.
   - Primary keys use UUID v4 strings, ensuring zero ID collision when migrating to multi-node PostgreSQL/CockroachDB.
   - The storage layer encapsulates SQL statements inside `backend/services/storage/activity_store.py` so database driver swaps require zero changes to FastAPI route handlers.

---

# Database Principles

Every table should:

- Have a primary key
- Use foreign keys
- Track timestamps
- Avoid duplicate data
- Be easy to scale

The database should prioritize maintainability over premature optimization.