# 5. CORS (Cross-Origin Resource Sharing) Configuration

## The Problem
Web browsers have a strict security rule: a website hosted on `https://my-frontend.com` is not allowed to talk to an API hosted on `https://my-backend.com` unless the backend explicitly gives it permission. The old code used `allow_origins=["*"]`, which is dangerous and sometimes gets blocked by strict browsers.

## Why It's Bad
- The frontend app will show "Network Error" and fail to load any data.
- Using `*` allows malicious websites to make requests to your API on behalf of your users.

## The Fix
We added a proper, secure CORS configuration. You can now define exactly which frontend websites are allowed to talk to your backend.

## How to Use It
Open your `.env` file and set the allowed frontend URLs: