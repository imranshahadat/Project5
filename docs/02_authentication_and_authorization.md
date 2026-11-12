
# 2. Authentication & Authorization

## The Problem
The old API was completely open to the public. Anyone on the internet could upload files, read chat histories, or delete documents without logging in.

## Why It's Bad
- **Security Breach**: Strangers can steal or delete your data.
- **Massive Bills**: Bots can spam your API, draining your AWS, Pinecone, and AI API budgets in minutes.

## The Fix
We added **JWT (JSON Web Token) Authentication**. 
Now, before a user can do anything, they must log in and get a special digital "key" (a token). Every time they make a request, they must show this key. If the key is missing or fake, the app blocks them.

## How to Use It
1. Generate a strong secret key in your `.env` file: `JWT_SECRET_KEY="your-secret-key-here"`
2. When a user logs in, your app gives them a token.
3. The frontend must send this token in the request headers like this:
   `Authorization: Bearer <your-token-here>`
4. If a request comes in without this header, the app automatically returns a `401 Unauthorized` error.