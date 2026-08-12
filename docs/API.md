# TravelSync API Specification

Base URL

/api/v1

---

# Authentication

POST /auth/register

Create a new account.

Request

{
    "username": "",
    "email": "",
    "password": ""
}

Response

{
    "user_id": "",
    "token": ""
}

--------------------------------------------------------

POST /auth/login

--------------------------------------------------------

POST /auth/logout

--------------------------------------------------------

GET /auth/profile

--------------------------------------------------------

# Trips

POST /trips

Create a trip.

Request

{
    "title": "",
    "source": "",
    "destination": "",
    "start_date": "",
    "end_date": "",
    "travelers": []
}

Response

{
    "trip_id": ""
}

--------------------------------------------------------

GET /trips

Return all user trips.

--------------------------------------------------------

GET /trips/{trip_id}

Return complete trip.

--------------------------------------------------------

PUT /trips/{trip_id}

Update trip.

--------------------------------------------------------

DELETE /trips/{trip_id}

Delete trip.

--------------------------------------------------------

# Planner

POST /planner

Generate trip.

Request

TripRequest

Response

TripResponse

--------------------------------------------------------

POST /planner/replan

Regenerate itinerary.

--------------------------------------------------------

POST /planner/optimize

Optimize existing trip.

--------------------------------------------------------

# Travelers

POST /trips/{trip_id}/members

Invite member.

--------------------------------------------------------

GET /trips/{trip_id}/members

--------------------------------------------------------

DELETE /trips/{trip_id}/members/{id}

--------------------------------------------------------

PATCH /trips/{trip_id}/members/{id}

Update member role.

--------------------------------------------------------

# Invitations

POST /invite

Generate invite link.

--------------------------------------------------------

GET /invite/{token}

Preview invitation.

--------------------------------------------------------

POST /invite/{token}/accept

--------------------------------------------------------

POST /invite/{token}/reject

--------------------------------------------------------

# Preferences

GET /preferences

--------------------------------------------------------

PUT /preferences

--------------------------------------------------------

GET /trips/{trip_id}/preferences

--------------------------------------------------------

PUT /trips/{trip_id}/preferences

--------------------------------------------------------

# Governance

POST /proposal

Create proposal.

--------------------------------------------------------

GET /proposal/{id}

--------------------------------------------------------

GET /trip/{trip_id}/proposals

--------------------------------------------------------

PATCH /proposal/{id}

--------------------------------------------------------

DELETE /proposal/{id}

--------------------------------------------------------

# Voting

POST /proposal/{id}/vote

Vote.

Support

Oppose

Neutral

Abstain

--------------------------------------------------------

GET /proposal/{id}/results

--------------------------------------------------------

# Owner

POST /owner/transfer

--------------------------------------------------------

POST /owner/recall

--------------------------------------------------------

POST /owner/accept

--------------------------------------------------------

POST /owner/reject

--------------------------------------------------------

# Communication

GET /chat/{trip_id}

--------------------------------------------------------

POST /chat/{trip_id}

--------------------------------------------------------

DELETE /chat/message/{id}

--------------------------------------------------------

PUT /chat/message/{id}

--------------------------------------------------------

POST /chat/reaction

--------------------------------------------------------

# Concerns

POST /concern

Raise concern.

--------------------------------------------------------

GET /concerns

--------------------------------------------------------

PATCH /concern/{id}

--------------------------------------------------------

# Memories

POST /memory

Upload memory.

--------------------------------------------------------

GET /memory/{trip_id}

--------------------------------------------------------

DELETE /memory/{id}

--------------------------------------------------------

POST /memory/story

Generate AI story.

--------------------------------------------------------

POST /memory/timeline

Generate timeline.

--------------------------------------------------------

# Photos

POST /photo

--------------------------------------------------------

GET /photo/{trip_id}

--------------------------------------------------------

DELETE /photo/{id}

--------------------------------------------------------

# Time Capsule

POST /capsule

--------------------------------------------------------

GET /capsule/{trip_id}

--------------------------------------------------------

POST /capsule/reveal

--------------------------------------------------------

# Challenges

GET /challenge

--------------------------------------------------------

POST /challenge/start

--------------------------------------------------------

POST /challenge/complete

--------------------------------------------------------

GET /leaderboard

--------------------------------------------------------

# Expenses

POST /expense

--------------------------------------------------------

GET /expense/{trip_id}

--------------------------------------------------------

PUT /expense/{id}

--------------------------------------------------------

DELETE /expense/{id}

--------------------------------------------------------

GET /expense/settlement/{trip_id}

--------------------------------------------------------

# Notifications

GET /notifications

--------------------------------------------------------

PATCH /notifications/read

--------------------------------------------------------

DELETE /notifications/{id}

--------------------------------------------------------

# Settings

GET /settings

--------------------------------------------------------

PUT /settings

--------------------------------------------------------

# Connection Mode

POST /connection/request

--------------------------------------------------------

POST /connection/friend

--------------------------------------------------------

POST /connection/private

--------------------------------------------------------

# Statistics

GET /trip/{trip_id}/stats

--------------------------------------------------------

GET /user/stats

--------------------------------------------------------

# AI

POST /ai/chat

General assistant.

--------------------------------------------------------

POST /ai/story

--------------------------------------------------------

POST /ai/suggest

--------------------------------------------------------

POST /ai/explain

Explain recommendation.

--------------------------------------------------------

# Future APIs

Calendar

Flights

Hotels

Maps

Wearables

Marketplace

Offline Sync

Third Party Integrations